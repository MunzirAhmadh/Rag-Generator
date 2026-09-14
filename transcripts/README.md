# Transcripts

This directory is for session export transcripts.

## Exporting the opencode Session

Before submitting, export your opencode session transcript into this folder:

```bash
# From the project root
opencode export > transcripts/session_$(date +%Y%m%d_%H%M%S).md
```

Or manually copy the transcript content into a new `.md` file in this directory.

The transcript should capture the full build session including all prompts, tool uses, and outputs.