# TODO List

* EXP with UNKNOWN converted to MAP
* MACRO
* function operations like f+g, f*g, f^3, etc.
* unify FORM and VAL_LST

## Syntax Update  

* BIND  := VAR LIST ? INHERIT ? = EXP INFO ?
  * "VAR LIST = EXP" is convert to "VAR = LIST => EXP" before eval, but if INHERIT exists, it has some complications
* MATCH := EXP(LEFT) :: EXP(RIGHT)
  * evaluates to a local env - an empty local env is created at the beginning
  * RIGHT is evaluated but LEFT is not
  * if LEFT is not a list, then either it is a name, a value or it is a COMBINATION of names and values - if it is a name, bind it with RIGHT; if it is a value, check whether it is equal to RIGHT; otherwise further consideration is required
  * if the value of RIGHT is a list, for each item in LEFT, first check whether it is in the env: skip it if so otherwise match the item in RIGHT in the corresponding position with it; however, if the current item in LIST is **unpacked**, match it with a sub-list of EXP such that the number of remaining items in EXP equals that in LIST; if there are items remaining in LEFT, if they are all BINDs, then define them in the local env, otherwise it is an error
  * the order is important
* LIST  := @LST ( BIND | EXP UNPACK ? ) ,
  * items will be evaluated in order
  * after evaluating a BIND, it will return None; for any item that evaluates to None in LIST, remove it from LIST
  * UNPACK unpacks the value of EXP into LIST
* MAP   := EXP(FORM) => EXP(BODY)
  * a rule to be applied
  * MAP EXP
    apply MAP on EXP - FORM is matched to EXP so that a local env is created; then BODY is evaluated in this env
