# TODO List

* EXP with UNKNOWN converted to MAP
* inverse the order of OBJ:NAME pair to NAME:OBJ
* MACRO
* function operations like f+g, f*g, f^3, etc.
* maybe I should make a distinction between 'simplify' and 'evaluate'
  * the former does not require env; the latter does
* unify FORM and EXP; update matching
  * the only difference between FORM and EXP is whether it is evaluated
  * FORM will be simplified while EXP will be evaluated
  * when a FORM is matched with EXP, there could be
    * a match failure, like `2 :: 1`
    * a successful match, which defines names in the present env
* rename MAP to RULE

## Syntax Update  

* EVAL  := BIND | EXP
* BIND  := FORM:EXP INHERIT ? = BODY:EXP INFO ?
  * BODY is evaluated in a local env and FORM is simplified before *matching*
  * rules for matching
    * FORM is a single name: directly bind
    * FORM is an atomic value: check whether its equals BODY
    * FORM is a list
      * for each name in FORM, first check whether it is in the env: skip it if so otherwise match the item in BODY in the corresponding position
      * note that I should only check it is in the current env, not going up to its parents
      * however, if the current item in FORM is **unpacked**, match it with a sub-list of EXP such that the number of remaining items in EXP equals that in LIST
      * if there are items remaining in FORM, if they are all BINDs, then define them in the local env, otherwise it is an error
      * if there are items remaining in BODY, it is an error (BINDs in BODY have been removed in evaluation)
    * FORM is the application of a RULE: this defines a RULE
    * FORM is a combination of math operations: this may lead to solving an equation
  * BIND is not an EXP
* MATCH is merged into BIND
* LIST  := @LST ( EVAL UNPACK ? ) ,
  * items will be evaluated in order
  * after evaluating a BIND, it will return None; for any item that evaluates to None in LIST, remove it from LIST
  * UNPACK unpacks the value of EXP into LIST
    * if it is a list, extend the LIST
    * if it is an env, define all its bindings in the current env
* GEN_LST is renamed to GEN
  * the FORM in CONSTR could be a LIST with BINDs in it, so WITH can be discarded now
  * maybe FORM, if it is a LIST, can omit its outer bracket
* SEQ   := @GRP @SEQ EVAL ,
  * placed after GROUP to parse correctly
  * return the value of its last item
  * if its value is None, it will return the current env instead
  * () is not allowed
* 'this' is a special name, always evaluates to the current env
* AT    := @ ENV:EXP BODY:EXP
  * ENV is evaluated first and then BODY is evaluated in ENV
  * it will replace LET
* RULE  := FORM:EXP => BODY:EXP
  * a rule to be applied
  * MAP VAL:EXP
    apply MAP on EXP - this is equivalent to `@(FORM = VAL) BODY`
