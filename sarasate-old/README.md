# ***Sarasate***: A Strong Representation System for Network Policies

Policy information in computer networking today is hard to manage. This is in sharp contrast to relational data structured in a database that allows easy access. In this demonstration, we ask why cannot (or how can) turn network policies into relational data. Our key observation is that oftentimes a policy does not prescribe a single “definite” network state, but rather is an “incomplete” description of all the legitimate network states. Based on this idea, we adopt conditional tables and the usual SQL interface (a relational structure developed for incomplete database) as a means to represent and query sets of network states in exactly the same way as a single definite network snapshot. More importantly, like relational tables that improve data productivity and innovation, relational policies allow us to extend a rich set of data mediating methods to address the networking problem of coordinating policies in a distributed environment.

## **Prerequisites**

- Python 3 - dependencies
  - Z3 - [Z3 API in Python](https://www.cs.tau.ac.il/~msagiv/courses/asv/z3py/guide-examples.htm)
  - psycopg2 - [PostgreSQL database adapter for Python](https://www.psycopg.org/docs/)

- PostgreSQL
  - extension - plpython3u. Used to the user-defined functions which are to accommodate variables in c-table.
    ```postgres
    create extension plpython3u
    ```
## **Implementation**

Run Sarasate system:

```bash
cd sarasate  # change to sarasate directory
python sarasate.py # 
```

## **Toy examples**

**policy1** 

| dest   | path   | condition  |
| :---  | :----  | :--- |
| 1.2.3.4   | x | "x == [ABC]" |
| y   | z        | "y != 1.2.3.5", "y != 1.2.3.4"   |

**policy2**

| dest  | path  | flag  | condition |
| :---  | :---  | :---  | :---  |
| 1.2.3.4   | [ABC] | u | "u == 1"  |
| 5.6.7.8   | [ABC] | u | "u != 1"  |
| 1.2.3.4   | [AC]  | v | "v == 1"  |
| 5.6.7.8   | [AC]  | v | "v != 1"  |

### **example 1**

Create new policy by adding a new constrain *path != [ABC]* into policy1 using simple ***select*** query.

```postgres
/*simple query*/
SELECT * FROM policy1 WHERE not_equal(path, '[ABC]');
```

After entering this query, the sarasate will automatically generate three steps which needs to be executed on the postgres. The final results running on postgres are as follows:

| dest   | path   | condition  |
| :---  | :----  | :--- |
| y   | z        | "y != 1.2.3.5", "y != 1.2.3.4", "z != [ABC]"  |

### **example 2**

Joinning policy1 and policy2. It is a sequential application that applys policy1 before policy2.

```postgres
/*simple join*/
SELECT * FROM policy1(dest, path, condition) JOIN policy2(dest, path, flag, condition);
```

**result**:

| dest  | path  | flag  | condition |
| :---  | :---  | :---  | :---  |
| y | z | u | "u != 1", "y == 5.6.7.8", "z == [ABC]"  |
| y | z | v | "v != 1", "y == 5.6.7.8", "z == [AC]"  |
| 1.2.3.4   | x | u | "x == [ABC]", "u == 1"    |






