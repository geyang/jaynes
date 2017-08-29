# Moleskin, A Logging Utility for Python Debugging
<a href="figures/star%20nosed%20mole.jpg" target="_blank"><img src="figures/star%20nosed%20mole.jpg" alt="star nose mole" align="right" width="350px"></a>
## Todo
- [ ] Write examples and justify `moleskin`'s existence
- [ ] add pretty pictures of a `mole` and with a notebook.

### Done

- [x] rename `ledger` to `moleskin`! because I couldn't get the names:
    - `ledger`: because somebody took it.
    - `parchment`: because somebody took it (>.<)
    - `vellum`: they took the calf version too (o_O )
    
    So I decided on `moleskin`! The paper just gets softer :)
    
## Installation
```bash
pip install moleskin
```

## Usage

```python
from moleskin import Moleskin

M = Moleskin()

M.log('this is a log entry!')

# Moleskin gives really nice debug traces:
some_variable = "test"
M.debug(some_variable)


# Moleskin can also be used as a code timer:
import time
M.start(silent=True)
time.sleep(3.0)
M.split()
# Lap Time: 3.0084s
```

You can even log to a file!

```python
from moleskin import Moleskin

moleskin = Moleskin(file="./a_log_file.log")
moleskin.log('this is a log entry!')
# and it prints to both std out *and* the log file!
```

## To Develop

```bash
git clone https://github.com/episodeyang/moleskin.git
cd moleskin
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
