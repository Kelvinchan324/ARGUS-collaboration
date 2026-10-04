# Developer Setup

## Clone

```bash
git clone https://github.com/Kelvinchan324/ARGUS-collaboration.git
cd ARGUS-collaboration
git lfs install
```

The initial repository does not require downloading every upstream robot. Fetch
only the dependencies needed for the adapter you are working on, following the
robot page and the dependency register.

## Validate a change

```bash
python scripts/validate_repo.py
```

## Local configuration

Copy examples from `config/` to a machine-local file ignored by Git. Store API
keys in an operating-system secret store or your deployment system. Do not put
real robot IP addresses, Wi-Fi credentials, API keys, or customer data in Git.

## Git practice

Update `main`, create one branch per issue, commit small logical changes, and
open a pull request. Do not combine unrelated CAD, documentation, and software
changes in one review.
