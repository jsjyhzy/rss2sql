# RSS to SQL

Preserving your subscribed RSS feeds into a relational database.

## Specification

There are three `class` and a configuration file.

### Classes

1. *Class* ToolKit
    - This class define some useful static method to handle parsed feed

2. *Class* RSS
    - Just a representation of a single RSS feed item.

3. *Class* SQL
    - Creating table according to configuration file, call its **fetch** method to store data after that table created scuessfully.

### Configuration File

Thanks to the diversity of RSS feed, it is necessary to configure settings manually. Here is an example:

```yaml
rss:
  url: "https://share.dmhy.org/topics/rss/rss.xml"
  proxies:
    https: "https://127.0.0.1:1080"
sql:
  tablename: "dmhy"
  field:
    - name: id
      val: "x.get('id')"
      type: VARCHAR
      type_parameter: 256
      nullable: false
      primary_key: true
      autoincrement: false
    - name: title
      val: "x.get('title')"
      type: TEXT
    - name: link
      val: "x.get('link')"
      type: TEXT
    - name: pubtime
      val: "ToolKit.struct_time_To_datetime(x.get('published_parsed'))"
      type: TIMESTAMP
      index: true
    - name: summary
      val: "x.get('summary')"
      type: TEXT
```

Just remember the **x** in `val` denotes the *dict* instance of an item which parsed by `feedparser` library

## Usage

```python
from rss2sql import SQL
SQL('/path/to/configuration','uri://of:your@own/database').fetch()
```

## Dependency

- SQLAlchemy and its connector friends (only if you need them)
- feedparser