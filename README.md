# Jaynes, A Logging Utility for Python Debugging
<a href="figures/ETJaynes_defiant.jpg" target="_blank"><img src="figures/ETJaynes_defiant.jpg" alt="Defiant Jaynes" align="right" width="350px"></a>
## Todo

- [ ] get the initial template to work

### Done

    
## Installation

```bash
pip install jaynes
```

## Usage (**Show me the Mo-NAY!!:money:**)

```python
from jaynes import Jaynes

J = Jaynes()  # where you add aws configurations
J.call(fn, {some, data})
```

Jaynes does the following:

1. 

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
