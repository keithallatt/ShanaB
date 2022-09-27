
#### Variable Names
`([a-zA-Z_][a-zA-Z_0-9]*)`
![[vn_re.png]]

#### Type
`(int|float|string)`
![[types.png]]

#### Expression
`(Variable Name)|(((Variable Name)([\+\-\*.\/&|^]))|(~))(Variable Name)`
![[expression.png]]

#### Statement
`(Type)((Variable Name)(,\s(Variable Name))*)`
![[stmnt_declaration.png]]

`(Variable Name)=(Expression)`
![[stmnt_assignment.png]]

`(while|if)(\(Expression\))(\{ (Statement)* \})`
![[stmnt_flow_control.png]]







