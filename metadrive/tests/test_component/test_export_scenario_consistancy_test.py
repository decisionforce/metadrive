import os
import pickle
import shutil

import numpy as np

from metadrive.envs.metadrive_env import MetaDriveEnv
from metadrive.envs.real_data_envs.waymo_env import WaymoEnv
from metadrive.policy.idm_policy import IDMPolicy
from metadrive.policy.replay_policy import WaymoReplayEgoCarPolicy
from metadrive.scenario import ScenarioDescription as SD


def assert_scenario_equal(scenarios1, scenarios2, only_compare_sdc=False):
    # ===== These two set of data should align =====
    assert set(scenarios1.keys()) == set(scenarios2.keys())
    for k in scenarios1.keys():
        old_scene = scenarios1[k]
        new_scene = scenarios2[k]
        SD.sanity_check(old_scene)
        SD.sanity_check(new_scene)
        assert old_scene[SD.LENGTH] == new_scene[SD.LENGTH], (old_scene[SD.LENGTH], new_scene[SD.LENGTH])

        if only_compare_sdc:
            sdc1 = old_scene["sdc_track_index"]
            sdc2 = new_scene["sdc_track_index"]
            state_dict1 = old_scene[SD.TRACKS][sdc1]
            state_dict2 = new_scene[SD.TRACKS][sdc2]
            for k in state_dict1[SD.STATE].keys():
                assert np.all(state_dict1[SD.STATE][k] == state_dict2[SD.STATE][k])
            assert state_dict1[SD.TYPE] == state_dict2[SD.TYPE]

        else:
            assert set(old_scene[SD.TRACKS].keys()) == set(new_scene[SD.TRACKS].keys())
            for track_id, track in old_scene[SD.TRACKS].items():
                for k in new_scene[SD.TRACKS][track_id][SD.STATE]:
                    assert np.all(new_scene[SD.TRACKS][track_id][SD.STATE][k] == track[SD.STATE][k])
                assert new_scene[SD.TRACKS][track_id][SD.TYPE] == track[SD.TYPE]

        assert set(old_scene[SD.MAP_FEATURES].keys()) == set(new_scene[SD.MAP_FEATURES].keys())
        assert set(old_scene[SD.DYNAMIC_MAP_STATES].keys()) == set(new_scene[SD.DYNAMIC_MAP_STATES].keys())

        for map_id, map_feat in old_scene[SD.MAP_FEATURES].items():
            assert np.all(new_scene[SD.MAP_FEATURES][map_id]["polyline"] == map_feat["polyline"])
            assert new_scene[SD.MAP_FEATURES][map_id][SD.TYPE] == map_feat[SD.TYPE]

        for obj_id, obj_state in old_scene[SD.DYNAMIC_MAP_STATES].items():
            assert np.all(new_scene[SD.DYNAMIC_MAP_STATES][obj_id][SD.STATE] == obj_state[SD.STATE])
            assert new_scene[SD.DYNAMIC_MAP_STATES][obj_id][SD.TYPE] == obj_state[SD.TYPE]


def test_export_metadrive_scenario_reproduction(scenario_num=3, render_export_env=False, render_load_env=False):
    env = MetaDriveEnv(
        dict(start_seed=0, use_render=render_export_env, environment_num=scenario_num, agent_policy=IDMPolicy)
    )
    policy = lambda x: [0, 1]
    dir1 = None
    try:
        scenarios = env.export_scenarios(policy, scenario_index=[i for i in range(scenario_num)])
        dir1 = os.path.join(os.path.dirname(__file__), "test_export")
        os.makedirs(dir1, exist_ok=True)
        for i, data in scenarios.items():
            with open(os.path.join(dir1, "{}.pkl".format(i)), "wb+") as file:
                pickle.dump(data, file)
    finally:
        env.close()

    # Same environment, same config
    env = MetaDriveEnv(
        dict(start_seed=0, use_render=render_load_env, environment_num=scenario_num, agent_policy=IDMPolicy)
    )
    policy = lambda x: [0, 1]
    try:
        scenarios2 = env.export_scenarios(policy, scenario_index=[i for i in range(scenario_num)])
    finally:
        env.close()

    if dir1 is not None:
        shutil.rmtree(dir1)

    assert_scenario_equal(scenarios, scenarios2, only_compare_sdc=True)


def test_export_metadrive_scenario_easy(render_export_env=False, render_load_env=False):
    # ===== Save data =====
    scenario_num = 1
    env = MetaDriveEnv(
        dict(start_seed=0, map="S", use_render=render_export_env, environment_num=scenario_num, agent_policy=IDMPolicy)
    )
    policy = lambda x: [0, 1]
    dir1 = None
    try:
        scenarios = env.export_scenarios(policy, scenario_index=[i for i in range(scenario_num)])
        dir1 = os.path.join(os.path.dirname(__file__), "test_export")
        os.makedirs(dir1, exist_ok=True)
        for i, data in scenarios.items():
            with open(os.path.join(dir1, "{}.pkl".format(i)), "wb+") as file:
                pickle.dump(data, file)
    finally:
        env.close()

    # ===== Save data of the restoring environment =====
    env = WaymoEnv(
        dict(
            agent_policy=WaymoReplayEgoCarPolicy,
            waymo_data_directory=dir1,
            use_render=render_load_env,
            case_num=scenario_num
        )
    )
    try:
        scenarios_restored = env.export_scenarios(
            policy, scenario_index=[i for i in range(scenario_num)], render_topdown=True
        )
    finally:
        env.close()

    if dir1 is not None:
        shutil.rmtree(dir1)

    assert_scenario_equal(scenarios, scenarios_restored, only_compare_sdc=True)


def test_export_metadrive_scenario_hard(render_export_env=False, render_load_env=False):
    # ===== Save data =====
    scenario_num = 3
    env = MetaDriveEnv(
        dict(start_seed=0, map=7, use_render=render_export_env, environment_num=scenario_num, agent_policy=IDMPolicy)
    )
    policy = lambda x: [0, 1]
    dir1 = None
    try:
        scenarios = env.export_scenarios(policy, scenario_index=[i for i in range(scenario_num)])
        dir1 = os.path.join(os.path.dirname(__file__), "test_export")
        os.makedirs(dir1, exist_ok=True)
        for i, data in scenarios.items():
            with open(os.path.join(dir1, "{}.pkl".format(i)), "wb+") as file:
                pickle.dump(data, file)
    finally:
        env.close()

    # ===== Save data of the restoring environment =====
    env = WaymoEnv(
        dict(
            agent_policy=WaymoReplayEgoCarPolicy,
            waymo_data_directory=dir1,
            use_render=render_load_env,
            case_num=scenario_num
        )
    )
    try:
        scenarios_restored = env.export_scenarios(
            policy, scenario_index=[i for i in range(scenario_num)], render_topdown=True
        )
    finally:
        env.close()

    if dir1 is not None:
        shutil.rmtree(dir1)

    assert_scenario_equal(scenarios, scenarios_restored, only_compare_sdc=True)


def test_export_waymo_scenario(render_export_env=False, render_load_env=False):
    scenario_num = 3
    env = WaymoEnv(
        dict(
            agent_policy=WaymoReplayEgoCarPolicy,
            use_render=render_export_env,
            start_case_index=0,
            case_num=scenario_num
        )
    )
    policy = lambda x: [0, 1]
    dir = None
    try:
        scenarios = env.export_scenarios(policy, scenario_index=[i for i in range(scenario_num)], verbose=True)
        dir = os.path.join(os.path.dirname(__file__), "test_export")
        os.makedirs(dir, exist_ok=True)
        for i, data in scenarios.items():
            with open(os.path.join(dir, "{}.pkl".format(i)), "wb+") as file:
                pickle.dump(data, file)
        env.close()

        print("===== Start restoring =====")
        env = WaymoEnv(
            dict(
                agent_policy=WaymoReplayEgoCarPolicy,
                waymo_data_directory=dir,
                use_render=render_load_env,
                case_num=scenario_num
            )
        )
        for index in range(scenario_num):
            print("Start replaying scenario {}".format(index))
            env.reset(force_seed=index)
            done = False
            count = 0
            while not done:
                o, r, done, i = env.step([0, 0])
                count += 1
            print("Finish replaying scenario {} with step {}".format(index, count))
    finally:
        env.close()
        if dir is not None:
            shutil.rmtree(dir)


if __name__ == "__main__":
    # test_export_metadrive_scenario_reproduction(scenario_num=1)
    test_export_metadrive_scenario_easy(render_export_env=False, render_load_env=True)
    # test_export_metadrive_scenario_hard(render_export_env=True, render_load_env=True)
    # test_export_waymo_scenario(render_export_env=True, render_load_env=True)
