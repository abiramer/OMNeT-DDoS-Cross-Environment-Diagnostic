# Security and dual-use notice

This package contains simulation and defensive machine-learning workflows for
controlled DDoS research. Run traffic generation only on isolated systems you
own or are authorized to use. Do not direct generated traffic at public or
third-party networks.

The optional historical Flask interface is not distributed because its source
contains development credentials, legacy models, uploaded files, and database
assumptions. Any future web interface must disable debug mode outside local
development and add authentication, authorization, rate limiting, upload size
limits, strict file-type validation, secure secret management, audit logging,
and production hardening before exposure to a network.

Report accidental credential exposure or unsafe release content privately to
the corresponding author at `abir.amer@mubs.edu.lb` before opening a public
issue.

