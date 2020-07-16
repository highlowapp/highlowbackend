import sqlparse

schema = './schema.sql'

sql = ''

with open(schema, 'r') as file:
    sql = file.read()


statements = sqlparse.split(sql)
statements.pop(0)

for statement in statements:
    statement.replace('\n', '')

print(statements)