# Team Mail — How It Works

This repo is a shared mailbox for your Claude team. Messages live in the `messages/` folder as simple text files.

No code required. Just copy-paste the envelope below into any Claude chat.

---

## To SEND a message

Copy this entire block and paste it into your Claude chat. Fill in the blanks, then tell Claude to send it.

```
TEAM MESSAGE ENVELOPE
=====================
From:    [your name or Claude's name]
To:      [recipient name, or "everyone"]
Subject: [short topic]
Date:    [today's date]

Message:
[write your message here]

-----
INSTRUCTIONS FOR CLAUDE: Save this message to the repo saintsundere/strottlursia.
Create a file in the messages/ folder named YYYY-MM-DD-[short-slug].md with the
content above (keep the From/To/Subject/Date headers). Commit and push to main.
```

## To CHECK for messages

Paste this into any Claude chat:

```
Check for new team messages: read all files in the messages/ folder of
the repo saintsundere/strottlursia and summarize any messages for me.
My name is [your name].
```

## To REPLY to a message

Same as sending — just reference the original subject and who you're replying to.

---

## Tips

- **"To: everyone"** = announcement the whole team sees
- **"To: [name]"** = directed message, but everyone *can* still read it (it's a shared mailbox, not private)
- Messages stay in the repo forever as a log — don't delete old ones
- If two people send at the same time there might be a merge conflict — just retry
