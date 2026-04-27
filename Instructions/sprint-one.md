@Nikita, Anthony, Miguel

**Task Overview:**

You will build an abstract & internal system that will be used by the model to interact with tools used for the simulated bencmark. These will include emails, calendars, and todo lists.

**Tooling:**
Emailing APIs *(read/write)*
Calendar APIs *(read/write/delete)*
Todo's APIs *(read/write/delete)*

**Abstraction:**

`Calendar Object` w/ arbitrary start date attribute (e.g. January 1st, 2000)
- Plan for 100 day time period space from start date
- Allow for overlapping events
- Consider creating an `Event Object`
- Event added to calendar should be marked arbitrary by unique identifier string.

`Todo Object` w/ due date and creation date attributes
- Task added to calendar should be marked arbitrary by unique identifier string.

`Email Object`
Must include and store:
- Subject
- Creation date (timestamp)
- Sender
- Recipient(s) <array>
- Body

`Scenario Object`
- Array of `Email Objects`
- Ensure there is a scenario ID attribute
- Any additional attributes

**Interactibility:**

Create FastAPI APIs to interact with these objects accordingly. As previosuly mentioned: read, write or delete. 
Ensure there is sufficient guardian code to respond back to model in case something fails.

-----------------------------------------------

@Eyasu, Nalu

**Task Overview**

You will be building the pipeline that connects the Excel sheet of email representations and working with Nikita, Anthony and Miguel to traspass this information into abstract objects.
Additionally, you will begin research on planning MCP tooling systematically w/ RAG system for context-keeping.

**Excel-to-Code:**

Read the Excel file into a pandas `DataFrame` object. Process eaech field into a corresponding `Email` object.

*Promised Excel structure fields:*
- Scenario ID
- Subject
- Sender
- Body
- Recipient(s) <array>
- Success Criteria **internal usage**
- Puzzle Summary **Internal usage**

**Conext & API interaction Research:**

Plan MCP tool calling. Plan a RAG system implementation and connection for model context. This is a research task so it's ambiguous by design.
