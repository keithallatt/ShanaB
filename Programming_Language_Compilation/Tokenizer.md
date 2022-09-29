
https://regexper.com/


#### Variable Names
`([a-zA-Z_][a-zA-Z_0-9]*)`
![[vn_re.png]]

#### Type
`(int|float|string)`
![[types.png]]

#### Expression
`(Variable Name|Immediate)|(((Variable Name|Immediate)([\+\-\*\/&|^%]))|(~))(Variable Name|Immediate)`
*need to update image*
![[expression.png]]

#### Statement
`(Type)((Variable Name)(,\s(Variable Name))*)`
![[stmnt_declaration.png]]

`(Variable Name)=(Expression)`
![[stmnt_assignment.png]]

`(while|if)(\(Expression\))(\{ (Statement)* \})`
![[stmnt_flow_control.png]]







