---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

I added a `region` attribute to our StorageClient class and the startup code now logs
client.region. Forty unit tests went red with AttributeError because their FakeStorageClient
doubles don't have region. The reviewer says just add region to all the fakes. Should I?
