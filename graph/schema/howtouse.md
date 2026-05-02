# 01_create_constraints.cypher
如何在 Neo4j Browser 里执行？
打开：
http://localhost:7474
登录：
username: neo4j
password: password
把 01_create_constraints.cypher 的内容复制进去执行。
执行后检查 constraints：
SHOW CONSTRAINTS;

你应该能看到这些 constraint name：

datasheet_id_unique
equipment_id_unique
technical_parameter_id_unique
evidence_id_unique
extraction_run_id_unique
validation_issue_id_unique
concept_name_unique
parameter_type_name_unique
unit_symbol_unique
required_parameter_id_unique
allowed_unit_id_unique
relationship_definition_name_unique
可能遇到的小问题

如果 Neo4j Browser 报错说某些 constraint 已经存在，不用紧张。
我们用了：

IF NOT EXISTS

正常情况下不会重复创建。

如果报语法错误，通常是 Neo4j 版本太旧。你现在用的是：

neo4j:5

所以这个语法应该是可以的。

# 02...