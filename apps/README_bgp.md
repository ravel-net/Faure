# BGP simulation

`bgp` application is a realistic example about BGP simulation by using `sarasate`. 

## What’s the BGP simulation? 

We are mimicking the behavior of the BGP speaker as it receives announcement from their neighbors. Then, the BGP speaker will be going to reapply its policy to update its current best path. This update will be essentially implemented as a `sarasate` join. 

## Data Source


## Walkthrough

1. Run Faure system with `--onlydb` mode and enter in bgp terminal.
   
```bash
$ sudo python3 ravel.py --onlydb

$ravel> bgp
```

2. Before implement BGP simulation, we need to load BGP data first from BGP RouteView RIB file and UPDATE file. Here, we select some typical data.
   
```bash
$bgp> loaddemo
```


3. 