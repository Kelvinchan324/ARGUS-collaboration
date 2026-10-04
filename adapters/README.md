# Robot Adapters

Each folder is the boundary between the common ARGUS interface and one robot's
native API. An adapter owns translation, capability reporting, input validation,
timeouts, safe-state behavior, and test doubles. It must not make the cockpit
depend directly on a vendor or upstream SDK.

Folders are placeholders until existing integration code is reviewed. Add source
only through a focused pull request with a robot page and safe verification plan.
