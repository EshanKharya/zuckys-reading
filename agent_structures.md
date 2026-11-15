Okay, now we will work on the sematic analysis. 

# Agents and their purpose

## 1. Event Summarizer: 
Provides a summary of the event that happened: what was the converstaion about, who said what, hot takes if any, singling out if any, banter if any, emotional disturbances if any. Structure of the output should contain: 
- The event header:
    * user mapping [shortened username - actual username - involvement score, i.e., how involved was the individual in the discussion], 
    * event name in the format {event_name}{apt preposition/joining word}{date}
    * impact strength score 
    * event size (# of words, # of messages, # of involved participants)
- report
    * what was the conversation about
    * who said what and to whom
    * hot takes if any
    * singling out if any
    * banter if any
    * emotional disturbances if any
    * for high impact messages, carry the specific sentences told. Or else summary of the statement suffices
- footer: list of topics discussed like: football, philosophy, cricket, relationships, etc

## 2. Personality Roaster: 
Takes the event summary report and builds the persona for each member in the group. Also updates the personality roast for the individual with upocoming events. The personas are tweaked by providing more weightage to analysis drawn from events with high impact score + individual involvement score of the person being analyzed. The personality output for each individual should be:
- Name, Title (Personality Descriptor), {Personality apt emoji}
- Roast with callbacks to high impact events for the individual
- Strengths and Weaknesses
- Meta data: top 5 event ids

## 3. Relationship Guru:
Takes the event summary report and builds the relationship matrix for all the participants in the conversation. Provides an overview of the relationship dynamics between all possible pairs in the group, while also maintaining the history of evolving relationships. The relationships are tweaked by providing more weightage to analysis drawn from events with high impact score + individual involvement score of the pair being analyzed. The relationship output for each pair should be:
- Person1-person2, a title for the couple, {couple apt emoji}
- Relationship Timeline: A short paragraph describing the current relationship between person1 and person2 in the context and how it has evolved over time (if any)
- Relationship Traits: Charecteristics of the relationship
- Strength Score: 1-10, 10 being in love.

## 4. Group Therapist:
Once all events are summarized and the personality + relationship meta data is ready, the group therapist takes all of the information and provides an overview of the group as a whole. The output should be:
- Group Identity: A title for the group, {group apt emoji}
- Group Timeline: A short paragraph describing the current group dynamic and how it has evolved over time (if any)
- Group Roast: A roast of the entire group with callbacks to high impact events
- Meta data: top 10 event ids.


# Events and Input Compression Strategy

An event is described exactly as it is in the static analysis. A conversation that is demarked with a 2 hour silence. Before providing the agents with any input, it is imperative to compress the event programatically, instead of picking up the raw txt export. Compression strategies that we can use are:

Note: Any modulated text for compression purposes will be demarked with %{text}%.

1. Replace lengthy usernames and mentions (@ based mentions) with short user codes. Provide the user code mapping in the event header. We create the user codes as %U1%, %U2%, %U3% ... in alphabetical order based on the username before even starting the analysis of events and store it in memory of the program. Before an event is sent to the agents, replace all occurrences of the usernames with the usercodes and add the map of only involved users in the header.
2. Remove timestamps of the messages sent. Instead, add the start timestamp and duration of the event in the header.
3. Remove the media omitted, message deleted and system generated messages like "You added {username}", "{username} added you", "{username} changed the name of the group to {group name}", "{username} left the group" etc. 
4. Emoji compression: If there are more than 3 emojis sent in a contiguous string, replace it with %{emoji}x{count}%.
5. Replace mentions (for example, ⁨username⁩) with %usercode%.
6. If a user has sent multiple messages without being interrupted by any other user, merge the messages with %% demarkation.

Compressed events will also be stored under /artifacts/{chat_name}/events folder and will be provided with an event_id in the filename. Event id will be E{integer}. The header will also contain the event id.

# Agent Orchestration

## Approach 1: Sequential Analysis

1. The event summarizer runs first and generates reports in outputs/{chatname}/event_reports/E{event_id}.md. The report header is code parsable. We will maintain an event_map.csv that will contain 
Event_id | event_name | duration | impact_strength | event_size | individual_involvement_score for each group member in order of the user code.

2. Next, the personality roaster runs through for each username in alphabetical order of the user code. It takes the event reports in order of the highest trait_marking_score where trait_marking_score = individual_involvement_score * impact_strength score. For top 20% trait_marking_scores, it takes the report and the compressed event as input. For top 20-50% or trait_marking_score > 50 (whichever is bigger) trait marking scores, it takes multiple reports at once with a limit of (not sure how i should define character/token limit). It ignores all other events. These decisions are made programmatically and stored in an in-memory datastructure: 

List of PersonDecision objects with the following attributes: 
- User Code
- List of high trait_marking events
- List of regular trait_marking events

When the agent spins up, the code simply follows the decisions made above to pull the reports and events and run the analysis. Since it keeps on running with every new event summary, it keeps updating the personality output for the individual with every input and stores the personality reports in outputs/{chatname}/personality_reports/{user_code}.md

3. Next, the relationship guru runs through for each pair of users in alphabetical order of the user code. It takes the event reports in order of the highest interaction_score for that pair
where interaction_score = Geometric mean of trait_marking_scores of each user in the pair.
For top 20% interaction_scores, it takes the report and the compressed event as input. For top 20-50% or interaction_scores > 50 (whichever is bigger), it takes multiple reports at once with a limit of (not sure how i should define character/token limit). It ignores all otehr events. These decisions are made programmatically and stored in an in-memory datastructure: 

List of PairDecision objects with the following attributes: 
- User Code 1
- User Code 2
- List of high interaction events
- List of regular interaction events

When the agent spins up, the code simply follows the decisions made above to pull the reports and events and run the analysis. Since it keeps on running with every new event summary, it keeps updating the personality output for the individual with every input and stores the relationship reports in outputs/{chatname}/relationship_reports/{user_code1}_{user_code2}.md

4. Takes the top 20% events with the highest group_impact_score which is calculated as Mean(involvement_score) * impact_score along with the compressed event. Takes the top 20-50% events or events with group_impact_score > 50 (whichever is bigger) without compressed events. It ignores all other events. These decisions are made programmatically and stored in an in-memory datastructure: 

List of GroupDecision objects with the following attributes: 
- List of high group impact events
- List of regular group impact events

When the agent spins up, the code simply follows the decisions made above to pull the reports and events and run the analysis. Since it keeps on running with every new event summary, it keeps updating the personality output for the individual with every input and stores the group output in outputs/{chatname}/group_report.md

5. I am also planning on running a group learner agent parallely to the event reporter, personality roast and relationship guru agents. This agent is basically supposed to learn the group dynamics with every oncoming event report/compressed raw event and provide context to each of these agents when they are running. This is because with every input their context would be flushed, so they wouldn't know how to judge things like impact_score, individual_involvement_score, relationship_strength, etc. But im scared of crashing my GPU due to VRAM overflow. How do you think i should ensure context is not lost and workflow actually adapts to different groups and makes judgements?


