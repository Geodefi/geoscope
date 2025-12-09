# Geoscope

- [Geoscope](#geoscope)
  - [What is geoscope?](#what-is-geoscope)
    - [How it works?](#how-it-works)
    - [What geoscope does not do](#what-geoscope-does-not-do)
    - [What geoscope does](#what-geoscope-does)
  - [Installation](#installation)
    - [Using pipx](#using-pipx)
    - [Using a Binary Executable](#using-a-binary-executable)
    - [Build from source](#build-from-source)
  - [Configuration](#configuration)
    - [1. Register to multisig](#1-register-to-multisig)
    - [2. Create a .geoscope folder](#2-create-a-geoscope-folder)
      - [config.json](#configjson)
      - [.env](#env)
    - [3. Setting up the gas api](#3-setting-up-the-gas-api)
    - [4. Setting up the notification service](#4-setting-up-the-notification-service)
  - [Running geoscope](#running-geoscope)
    - [with pipx](#with-pipx)
    - [with Binary](#with-binary)
    - [with source files](#with-source-files)
  - [Commands \& Flags](#commands--flags)
  - [Contacts](#contacts)
  - [License](#license)

## What is geoscope?

Geoscope is a multi*daemon*tial oracle application that provides required checks and data updates for [geoDefi](https://www.geode.fi) contracts

### How it works?

Geoscope keeps track of all the validators proposed through geodefi's Portal, and reates multiple daemons for 3 main tasks:

- Approving validator proposals by checking validators are not acting malicious for the proposal stage and lets them to stake by incresing the verification index
- Create and push balance and price merkles to supply required data for the Portal from the beacon chain.
- Informing Portal to imprison malicious node operators in cases:
  - Proposing malicious validator during *proposeStake*
  - Fee theft situations
  - Not exitting when required to exit

> There are multiple daemons that are required to do different tasks like; listening beacon chain for withdrawals and deposits, checking verification indexes or creating merkles in timely manner.
>
> Check [this document](docs/daemons.md) to learn more about these daemons.

### What geoscope does not do

- Does not realy on one party, need a consensys to take actions.
- Does not update prices on gETH, you need to call *priceSync* function for that.
- Does not send exit requests or force to exit any validator, users and node operators should take actions for that.
- Does not call stake after approving validators, delegates to geonius for that. # This is faulty: was geonious
- Does not trust you or your friends.

### What geoscope does

- Help you with its configuration.
- Validate new validators that are created through *proposeStake*.
- Allow proposed validators to be staked.
- Track all the deposits and withdrawals on beacon chain and update Portal with necessary calculations by pushing merkles.
- Make sure there is no fee theft is happening
- Inform Portal for maliciously acting operators to be imprisoned.
- Checks if the gas is ok, before submitting a transaction.
- Mails to its owners when there is a matter of importance.
- Refuses to eleborate and leaves (sometimes). So, it is crucial to check if it is still alive every now and then.

## Installation

### Using pipx

> **Preferred**
>
> [pipx](https://pipx.pypa.io/stable/) is the go-to choice for executable python applications.
> Running this app with pipx will make it easy to update, and less error prone compared to using a binary executable or building from source.

```bash
pipx install geoscope
```

Pipx installation requires python version between **3.8** to **3.12**.

Check out [this document](./docs/installation_guide.md) if you need help or suggestions on this.

### Using a Binary Executable

Binaries for the latest version of geoscope can be obtained from the [releases page](https://github.com/Geodefi/geoscope/releases).

Simply, locate and download the suitable one for your operation system.

### Build from source

Check out [this document](./docs/installation_guide.md).

## Configuration

### 1. Register to multisig

Before configuration you need to be added to multisig, GeoDefi team probably already reached you out and you are probably here because of that. If you are already included to multisig you can continue with the next step.

### 2. Create a .geoscope folder

> Note that, this is unnecessary and `geoscope config` command will create one for you. However, if you want to make sure everything is perfect, or if you already have a configuration file (config.json) or an environment file (.env) that you want to use and skip the `geoscope config` step; you can.
>
> Alternatively;
>
> ```bash
> geoscope config
> ```

This folder should be placed under the same parent folder where the geoscope script will run.

It will be used for the database, store the log files and keep the configuration file for you.

#### config.json

A sample config.json with gas and email services activated can be found [here](./.geoscope/config.json).

If you want to understand the meaning of the fields, you can check [Commands \& Flags](#commands--flags).

#### .env

A sample .env can be found [here](./.geoscope/.env.sample). Below you can find descriptions of required and optional environment parameters.

- `GEOSCOPE_PRIVATE_KEY` : private key for the address which already added to multisig that will run geoscope.
- `EMAIL_PASSWORD` : special passphrase of your arranged gmail address that can be used by other apps.
- `API_KEY_EXECUTION` : (optional) api key that will be changed with the "<API_KEY_EXECUTION>" section of the execution layer api string. Not needed if the endpoint does not need a key.
- `API_KEY_CONSENSUS` : (optional) api key that will be changed with the "<API_KEY_CONSENSUS>" section of the consensus layer api string. Not needed if the endpoint does not need a key.
- `API_KEY_GAS` : (optional) api key that will be changed with the "<API_KEY_GAS>" section of the gas api string. Not needed if the endpoint does not need a key.

### 3. Setting up the gas api

> Not suggested for holesky deployments.

Simply, you can provide any endpoint that responds as **gwei**, which will be used as a gas price oracle.
Moreover, you can add maximum limits to the base and priority fees when api is provided.

Note that you can also create a custom parser! For example, if the response has a body that looks like this, and you want to choose the "high" option.

```json
{
  "low":..,
  "mid":..,
  "high": {"base":0,"priority":0}
}
```

Then you can provide the parser as :
{
"base": "high.base",
"priority": "high.priority"
}

For an easy setup, visit [infura](https://docs.infura.io/api/infura-expansion-apis/gas-api/api-reference/gasprices-type2) and aquire an app key. Then you can use the default parsers on the configuration step.

### 4. Setting up the notification service

You can configure this service easily so geoscope send you regular updates or notifications on its current situation. This can be crucial if there is a bug and geoscope fully or partially stops.

Sign into gmail and head to: `https://myaccount.google.com/apppasswords`. Then you will acquire a passphrase like "xxx xxx xxx xxx". This password can be provided during the configuration with `passphrase config` or as `EMAIL_PASSWORD` directly in .env file.

Then all you need to do is to provide the mail addresses for receiver and sender.

> Note that, you can add many for the receiver field.

## Running geoscope

Up until this point, if you have:

1. Included into multisig
2. Installed geoscope with pipx, or downloaded it as a binary, or built it from source.
3. Configured it with `geoscope config`

Then, you are ready to start geoscope.

### with pipx

```bash
geoscope run --chain holesky
```

### with Binary

```bash
geoscope run --chain holesky
```

### with source files

Check out [this document](./docs/installation_guide.md).

## Commands & Flags

[Check out this document.](./docs/commands.md)

## Contacts

- Ice Bear - <admin@geode.fi>
- Crash Bandicoot - <bandicoot@geode.fi>

## License

`geoscope` is licensed under [MIT](./LICENSE).
