from src.opportunity_filter import is_opportunity


def test_infrastructure_article_is_not_campaign():
    assert not is_opportunity("5 Ways to Build With a Runtime Environment",
        "Build applications with our platform.\n" + "Infrastructure description. " * 30
        + "Join a testnet to learn.\nCollect rewards in third party quests.")


def test_community_awards_not_reward_for_voter():
    assert not is_opportunity("Community Awards: Meet the Finalists",
        "Vote for 48 finalists. Awards celebrate our ecosystem. Winners receive prizes.")
