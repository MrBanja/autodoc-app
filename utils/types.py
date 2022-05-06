from datetime import datetime, date

from sqlalchemy import Column

IntColumnType = int | Column
StrColumnType = str | Column
BoolColumnType = Column | bool
DateTimeColumnType = Column | datetime
DateColumnType = Column | date
