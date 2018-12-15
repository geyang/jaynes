# Jaynes, A Utility for training ML models on AWS, GCE, SLURM, with or without docker <a href="figures/ETJaynes_defiant.jpg" target="_blank"><img src="figures/ETJaynes_defiant.jpg" alt="Defiant Jaynes" align="right" width="350px" style="top:20px"></a>

[![Downloads](http://pepy.tech/badge/jaynes)](http://pepy.tech/project/jaynes)

## Todo

- [x] get the initial template to work

### Done

## Installation

```bash
pip install jaynes
```

## Usage (**Show me the Mo-NAY!! :moneybag::money_with_wings:**)

Check out the [test_projects](./test_projects) folder for projects that you can run. I just recenlty implemented a hugely improved API that uses a static `yaml` configuration file, so the documentations are still comming.

To try to get things to work via ssh/slurm/aws, see [test_projects](./test_projects).

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

## Acknowledgements

This code is inspired by @justinfu's [doodad](https://github.com/justinjfu/doodad), which is in turn built on top of Peter Chen's script.

This code is written from scratch to allow a more permissible open-source license (BSD). Go bears :bear: !!
