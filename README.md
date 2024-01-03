# Probe
A Geometry Dash Proxy Validator Used for finding proxies that are not banned by Robtop
Because my god, Robtop and the Eldermods, love to throw wrenches into my work. 
Most Free proxies don't make it passed rubrub's firewall so I made a tool that 
at least helps me find the ones that still are working.

Probe uses extremely minimal bandwith to find proxies that work and I made sure of that by 
checking how the server behaves and how can I test these things in such a way where I don't 
over-stress the servers...

# How to use
```
python probe.py --help
```

Probe uses a module called `asyncclick` to create a clean commandline in asyncio. 
it is possible to take the class object I made and then attempt to implement it 
into your own code but I will document that stuff later...


