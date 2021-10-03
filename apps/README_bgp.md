# BGP simulation

`bgp` application is a realistic example about BGP simulation by using `sarasate`. 

What’s the BGP simulation? We are mimicking the behavior of the BGP speaker as it receives announcement from their neighbors. Then, the BGP speaker will be going to reapply its policy to update its current best path. This update will be essentially implemented as a sarasate join. 