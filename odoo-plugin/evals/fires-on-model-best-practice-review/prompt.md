---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

Can you review this Odoo 17 model before we merge it?

```python
class LibraryBook(models.Model):
    _name = 'library.book'

    name = fields.Char()
    isbn = fields.Char()

    def get_count(self):
        return len(self.search([]))
```
