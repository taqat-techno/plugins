---
max_turns: 8
allowed_tools: [Skill]
tags: [routing]
---

Review this SQLAlchemy model for problems:

```python
class Book(Base):
    __tablename__ = 'books'
    id = Column(Integer, primary_key=True)
    isbn = Column(String(13))
```
