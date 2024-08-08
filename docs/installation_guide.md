# Build from source

## Pyenv and Poetry

We do not recommend using `pip` and your local `python` packages.

Use `pyenv` to manage your python version.

Use `poetry` for dependency management and packaging.

Use `pipx` to manage your local packages, which should just be poetry for this instance.

## Install `pyenv`

Simply:

```bash
curl https://pyenv.run | bash
pyenv update
```

<!-- echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
exec $SHELL
pyenv update -->

## Install python v3.10 with `pyenv`

```bash
pyenv install 3.9
pyenv versions
```

## Install `pipx`

on Ubuntu 23.04 or above:

```bash
sudo apt update
sudo apt install pipx
pipx ensurepath
sudo pipx --global ensurepath
exec $SHELL
```

on MacOS:

```bash
brew install pipx
pipx ensurepath
sudo pipx --global ensurepath
exec $SHELL
```

## Install `poetry` with `pipx`

```bash
pipx install poetry
poetry config virtualenvs.prefer-active-python true
which poetry
```

#### Clone repos

```bash
git clone https://github.com/Geodefi/geoscope
cd geoscope
```

#### Create virtual env

```bash
poetry shell
```

#### Create virtual env with a specific version

```bash
poetry env use <python_version/3.9/3.9.19/etc>
```

This will output:

> Using virtualenv: <path_to_venv>
> copy <path_to_venv> and use it above to activate

```bash
source <path_to_venv>/bin/activate
```

## Running `geoscope` with poetry

```bash
git clone https://github.com/Geodefi/geoscope
cd geoscope
poetry install
```

Then, after cloning the repo you should create a dedicated folder with

```bash
poetry run geoscope config
```

Then, you can easily start geoscope with:

```bash
poetry run geoscope run
```

> In case you want to run it on background put `&` after the command:
>
> ```bash
> PYTHONPATH=. poetry run python src/main.py --flags &
> ```
