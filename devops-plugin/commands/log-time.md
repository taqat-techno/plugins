---
title: 'Log Time'
read_only: false
type: 'command'
description: 'Log working hours against work items or general categories'
---

# /log-time - Log Working Hours

Parse `$ARGUMENTS` for hours, work item ID, and optional category.

Examples:
```
/log-time 3h #1234              Log 3 hours on work item 1234
/log-time 2h meeting            Log 2 hours to "meeting" category
/log-time 1.5h #5678 "review"   Log 1.5 hours with description
```

Use the devops skill for:
- Time entry format and storage
- Work item hour update (CompletedWork, RemainingWork)
- Category management
- Daily/weekly compliance tracking
- Write operation gate for work item updates
