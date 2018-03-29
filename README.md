# Jaynes, A Logging Utility for Python Debugging
<a href="figures/star%20nosed%20mole.jpg" target="_blank"><img src="figures/star%20nosed%20mole.jpg" alt="star nose mole" align="right" width="350px"></a>
## Todo

- [ ] Write examples and justify `jaynes`'s existence
- [ ] add pretty pictures of a `mole` and with a notebook.

### Done

- [x] rename `ledger` to `jaynes`! because I couldn't get the names:
    - `ledger`: because somebody took it.
    - `parchment`: because somebody took it (>.<)
    - `vellum`: they took the calf version too (o_O )
    
    So I decided on `jaynes`! The paper just gets softer :)
    
## Installation

```bash
pip install jaynes
```

## Usage

```python
from jaynes import Jaynes

M = Jaynes()

M.log('this is a log entry!')

# Jaynes gives really nice debug traces:
some_variable = "test"
M.debug(some_variable)


# Jaynes can also be used as a code timer:
import time
M.start(silent=True)
time.sleep(3.0)
M.split()
# Lap Time: 3.0084s
```

You can even log to a file!

```python
from jaynes import Jaynes

jaynes = Jaynes(file="./a_log_file.log")
jaynes.log('this is a log entry!')
# and it prints to both std out *and* the log file!
```

## To Develop

```bash
git clone https://github.com/episodeyang/jaynes.git
cd jaynes
make dev
```

To test, run

```bash
make test
```

This `make dev` command should build the wheel and install it in your current python environment. Take a look at the [./Makefile](./Makefile) for details.

**To publish**, first update the version number, then do:

```bash
make publish
```
