# ***Sarasate***: A Strong Representation System for Network Policies

Policy information in computer networking today is hard to manage. This is in sharp contrast to relational data structured in a database that allows easy access. In this demonstration, we ask why cannot (or how can) turn network policies into relational data. Our key observation is that oftentimes a policy does not prescribe a single “definite” network state, but rather is an “incomplete” description of all the legitimate network states. Based on this idea, we adopt conditional tables and the usual SQL interface (a relational structure developed for incomplete database) as a means to represent and query sets of network states in exactly the same way as a single definite network snapshot. More importantly, like relational tables that improve data productivity and innovation, relational policies allow us to extend a rich set of data mediating methods to address the networking problem of coordinating policies in a distributed environment.

## **Prerequisites**

- Python 3
  - Z3 - [Z3 API in Python](https://www.cs.tau.ac.il/~msagiv/courses/asv/z3py/guide-examples.htm)
  - psycopg2 - [PostgreSQL database adapter for Python](https://www.psycopg.org/docs/)

- PostgreSQL
  - extension - plpython3u. Used to the user-defined functions which are to accomodate variables in c-table.
    ```postgres
    create extension plpython3u
    ```
## **Implement**


