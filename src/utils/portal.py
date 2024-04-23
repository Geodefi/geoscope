from geode.globals import ID_TYPE
from ..globals.sdk import SDK
from ..globals.config import CONFIG
from .multithread import multithread
from .attributeDict import AttributeDict

block_mode = CONFIG.chains[SDK.network.name].mode


def stake_params(block: int = block_mode) -> AttributeDict:
    res: list = SDK.Portal.contract.functions.StakeParams().call(block_identifier=block)

    return AttributeDict(
        {
            "gETH": res[0],
            "oraclePosition": res[1],
            "validatorsIndex": res[2],
            "verificationIndex": res[3],
            "monopolyThreshold": res[4],
            "oracleUpdateTimestamp": res[5],
            "dailyPriceIncreaseLimit": res[6],
            "dailyPriceDecreaseLimit": res[7],
            "governanceFee": res[8],
            "priceMerkleRoot": res[9],
            "balanceMerkleRoot": res[10],
        }
    )


def get_validator(pubkey: str, block: int = block_mode) -> AttributeDict:
    res: list = SDK.Portal.contract.functions.getValidator(pubkey).call(
        block_identifier=block
    )

    return AttributeDict(
        {
            "state": res[0],
            "index": res[1],
            "createdAt": res[2],
            "period": res[3],
            "poolId": res[4],
            "operatorId": res[5],
            "poolFee": res[6],
            "operatorFee": res[7],
            "governanceFee": res[8],
            "signature31": res[9],
        }
    )


def get_pool_id_by_index(index, block: int = block_mode) -> str:
    return str(
        SDK.Portal.contract.functions.allIdsByType(ID_TYPE.POOL, index).call(
            block_identifier=block
        )
    )


def get_all_pool_ids(block: int = block_mode) -> list:
    len: int = SDK.Portal.contract.functions.allIdsByTypeLength(ID_TYPE.POOL).call(
        block_identifier=block
    )

    ids: list = multithread(get_pool_id_by_index, (range(len)))

    return ids
