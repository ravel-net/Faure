
--Part 1: Features
-- When Policy1 and Policy2 are applied sequentially, the 
-- join table gives intuitive explanation of the combined polices

-- Policy1 -- P1 -- a policy that requires static route [ABC] for 1.2.3.4 and filters 1.2.3.5; R: (fragment of) current routing
--state (candidate routes learned from some routing protocol);

---------------------------------------------------
--Part 1: Features
--Policy1 -- P1 -- a policy that requires static route [ABC] for 1.2.3.4 and filters 1.2.3.5; 
DROP TABLE IF EXISTS Policy1 CASCADE;
create table Policy1 ( DEST TEXT, PATH TEXT, CONDITION TEXT []);
insert into Policy1 ( DEST,PATH,CONDITION) values 
('1.2.3.4','x','{"x == [ABC]"}'),
('y','z','{"y != 1.2.3.5", "y != 1.2.3.4"}');

--Policy2 -- P2 -- a policy that balances traffic for 1.2.3.4 and 5.6.7.8;
DROP TABLE IF EXISTS Policy2 CASCADE;
create table Policy2 ( DEST TEXT, PATH TEXT, FLAG TEXT, CONDITION TEXT []);
insert into Policy2 ( DEST,PATH,FLAG,CONDITION) values 
('1.2.3.4','[ABC]', 'u', '{"u == 1"}'),
('5.6.7.8','[ABC]', 'u', '{"u != 1"}'),
('1.2.3.4','[AC]', 'v', '{"v == 1"}'),
('5.6.7.8','[AC]', 'v', '{"v != 1"}');

--Policy3 -- P3 -- a policy that requires static route [AC] for 1.2.3.4; 
DROP TABLE IF EXISTS Policy3 CASCADE;
create table Policy3 ( DEST TEXT, PATH TEXT, CONDITION TEXT []);
insert into Policy3 ( DEST,PATH,CONDITION) values 
('1.2.3.4','x','{"x == [ADC]"}');

-- Routing: Routing table 
DROP TABLE IF EXISTS Routing CASCADE;
create table Routing ( DEST TEXT, PATH TEXT,CONDITION TEXT []);
insert into Routing ( DEST,PATH, CONDITION) values 
('1.2.3.4','[ABC]','{}'),
('1.2.3.4','[AC]','{}'),
('1.2.3.5','[ADC]','{}'),
('5.6.7.8','[ABC]','{}'),
('5.6.7.8','[AC]','{}');

-- I1: Instance for p1
DROP TABLE IF EXISTS I1 CASCADE;
create table I1 ( DEST TEXT, PATH TEXT,CONDITION TEXT []);
insert into I1 ( DEST,PATH, CONDITION) values 
('1.2.3.4','[ABC]','{"[ABC] == [ABC]"}'),
('5.6.7.8','[AC]','{"5.6.7.8 != 1.2.3.5", "5.6.7.8 != 1.2.3.4"}');

DROP TABLE IF EXISTS I1_ CASCADE;
create table I1_ ( DEST TEXT, PATH TEXT,CONDITION TEXT []);
insert into I1_ ( DEST,PATH, CONDITION) values 
('1.2.3.4','[ABC]','{}'),
('5.6.7.8','[AC]','{}');

-- I2: Instance for p1
DROP TABLE IF EXISTS I2 CASCADE;
create table I2 ( DEST TEXT, PATH TEXT,CONDITION TEXT []);
insert into I2 ( DEST,PATH, CONDITION) values 
('1.2.3.4','[AC]','{"[AC] == [ABC]"}'),
('1.2.3.5','[ADC]','{"1.2.3.5 != 1.2.3.5", "1.2.3.5 != 1.2.3.4"}');

--1.Features:
--1.1:
--SELECT * FROM POLICY1 where not_equal(path,'[ADC]');
--1.2
-- SELECT * FROM policy1( DEST,PATH,COND) JOIN routing( DEST,PATH, COND) ;  
--1.3
--SELECT * FROM policy1( DEST,PATH,COND) JOIN routing( DEST,PATH, COND) WHERE not_equal(path,'[ABE]');  
--1.4 
--this can be used in BGP UPDATE 




--------------------------------------------------------
-- Part2: Policy Exchange 
-- Policy exchange: P2 and P3 represent the local policies of X and A; P3’ represents impact of X on A. 
--Merging PX’ into PA gives PA’, a new policy that forces A to take into account the requirement of X.
-- Policy2 -- Px'
-- DROP TABLE IF EXISTS Policy2 CASCADE;
-- create table Policy2 ( DEST TEXT, PATH TEXT, COND TEXT []);
-- insert into Policy2 ( DEST,PATH,COND) values 
-- ('10.0.0.1','u','{"l(u) < 2"}');

-- --Policy3 -- Pa 
-- DROP TABLE IF EXISTS Policy3 CASCADE;
-- create table Policy3 ( DEST TEXT, NH TEXT, FLAG TEXT, COND TEXT []);
-- insert into Policy3 ( DEST,NH, FLAG, COND) values 
-- ('10.0.0.1','C','x','{"x == 1"}'),
-- ('10.0.0.1','D','y','{"y == 1"}'),
-- ('10.0.0.2','C','x','{"x != 1"}'),
-- ('10.0.0.2','D','y','{"y != 1"}');

-- SELECT * FROM Policy2(DEST,PATH,COND) JOIN Policy3(DEST,NH, FLAG, COND);


