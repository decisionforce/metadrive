import os
import pickle
import shutil

import numpy as np

from metadrive.envs.metadrive_env import MetaDriveEnv
from metadrive.envs.real_data_envs.waymo_env import WaymoEnv
from metadrive.policy.idm_policy import IDMPolicy
from metadrive.policy.replay_policy import WaymoReplayEgoCarPolicy
from metadrive.scenario import ScenarioDescription as SD

NP_ARRAY_DECIMAL = 4
VELOCITY_DECIMAL = 1  # velocity can not be set accurately


def assert_scenario_equal(scenarios1, scenarios2, only_compare_sdc=False):
    # ===== These two set of data should align =====
    assert set(scenarios1.keys()) == set(scenarios2.keys())
    for k in scenarios1.keys():
        old_scene = scenarios1[k]
        new_scene = scenarios2[k]
        SD.sanity_check(old_scene)
        SD.sanity_check(new_scene)
        assert old_scene[SD.LENGTH] >= new_scene[SD.LENGTH], (old_scene[SD.LENGTH], new_scene[SD.LENGTH])

        if only_compare_sdc:
            sdc1 = old_scene[SD.METADATA][SD.SDC_ID]
            sdc2 = new_scene[SD.METADATA][SD.SDC_ID]
            state_dict1 = old_scene[SD.TRACKS][sdc1]
            state_dict2 = new_scene[SD.TRACKS][sdc2]
            min_len = min(state_dict1[SD.STATE]["position"].shape[0], state_dict2[SD.STATE]["position"].shape[0])
            for k in state_dict1[SD.STATE].keys():
                if k in ["action", "throttle_brake", "steering"]:
                    continue
                elif k == "position":
                    np.testing.assert_almost_equal(
                        state_dict1[SD.STATE][k][:min_len][..., :2],
                        state_dict2[SD.STATE][k][:min_len][..., :2],
                        decimal=NP_ARRAY_DECIMAL
                    )
                elif k == "heading":
                    np.testing.assert_almost_equal(
                        state_dict1[SD.STATE][k][:min_len],
                        state_dict2[SD.STATE][k][:min_len],
                        decimal=NP_ARRAY_DECIMAL
                    )
                elif k == "velocity":
                    np.testing.assert_almost_equal(
                        state_dict1[SD.STATE][k][:min_len],
                        state_dict2[SD.STATE][k][:min_len],
                        decimal=VELOCITY_DECIMAL
                    )
            assert state_dict1[SD.TYPE] == state_dict2[SD.TYPE]

        else:
            assert set(old_scene[SD.TRACKS].keys()) == set(new_scene[SD.TRACKS].keys())
            for track_id, track in old_scene[SD.TRACKS].items():
                for k in new_scene[SD.TRACKS][track_id][SD.STATE]:
                    state_array_1 = new_scene[SD.TRACKS][track_id][SD.STATE][k]
                    state_array_2 = track[SD.STATE][k]
                    min_len = min(state_array_1.shape[0], state_array_2.shape[0])
                    np.testing.assert_almost_equal(
                        state_array_1[:min_len], state_array_2[:min_len], decimal=NP_ARRAY_DECIMAL
                    )
                assert new_scene[SD.TRACKS][track_id][SD.TYPE] == track[SD.TYPE]

        assert set(old_scene[SD.MAP_FEATURES].keys()) == set(new_scene[SD.MAP_FEATURES].keys())
        assert set(old_scene[SD.DYNAMIC_MAP_STATES].keys()) == set(new_scene[SD.DYNAMIC_MAP_STATES].keys())

        # TODO FIXME: The polyline is reversed in 2nd dim. Need to take care of this.
        #  Temporarily disable the test
        # for map_id, map_feat in old_scene[SD.MAP_FEATURES].items():
        #     np.testing.assert_almost_equal(
        #         new_scene[SD.MAP_FEATURES][map_id]["polyline"], map_feat["polyline"], decimal=NP_ARRAY_DECIMAL
        #     )
        #     assert new_scene[SD.MAP_FEATURES][map_id][SD.TYPE] == map_feat[SD.TYPE]

        for obj_id, obj_state in old_scene[SD.DYNAMIC_MAP_STATES].items():
            np.testing.assert_almost_equal(
                new_scene[SD.DYNAMIC_MAP_STATES][obj_id][SD.STATE], obj_state[SD.STATE], decimal=NP_ARRAY_DECIMAL
            )

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


def test_export_metadrive_scenario_easy(scenario_num=2, render_export_env=False, render_load_env=False):
    # ===== Save data =====
    env = MetaDriveEnv(
        dict(start_seed=0, map="S", use_render=render_export_env, environment_num=scenario_num, agent_policy=IDMPolicy)
    )
    policy = lambda x: [0, 1]
    dir1 = None
    try:
        scenarios = env.export_scenarios(policy, scenario_index=[i for i in range(scenario_num)])
        dir1 = os.path.join(os.path.dirname(__file__), "test_export_scenario_consistancy")
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
            policy, scenario_index=[i for i in range(scenario_num)], render_topdown=render_load_env
        )
    finally:
        env.close()

    if dir1 is not None:
        shutil.rmtree(dir1)

    assert_scenario_equal(scenarios, scenarios_restored, only_compare_sdc=True)


def test_export_metadrive_scenario_hard(scenario_num=3, render_export_env=False, render_load_env=False):
    # ===== Save data =====
    env = MetaDriveEnv(
        dict(start_seed=0, map=7, use_render=render_export_env, environment_num=scenario_num, agent_policy=IDMPolicy)
    )
    policy = lambda x: [0, 1]
    dir1 = None
    try:
        scenarios = env.export_scenarios(policy, scenario_index=[i for i in range(scenario_num)])
        dir1 = os.path.join(os.path.dirname(__file__), "test_export_metadrive_scenario_hard")
        os.makedirs(dir1, exist_ok=True)
        for i, data in scenarios.items():
            with open(os.path.join(dir1, "{}.pkl".format(i)), "wb+") as file:
                pickle.dump(data, file)
    finally:
        env.close()
        # pass

    # ===== Save data of the restoring environment =====
    env = WaymoEnv(
        dict(
            agent_policy=WaymoReplayEgoCarPolicy,
            waymo_data_directory=dir1,
            use_render=render_load_env,
            case_num=scenario_num,
            debug=True,
            # debug_physics_world=True,
            # debug_static_world=True
        )
    )
    try:
        scenarios_restored = env.export_scenarios(
            policy, scenario_index=[i for i in range(scenario_num)], render_topdown=False
        )
    finally:
        env.close()

    if dir1 is not None:
        shutil.rmtree(dir1)

    assert_scenario_equal(scenarios, scenarios_restored, only_compare_sdc=True)


def WIP_test_export_waymo_scenario(scenario_num=3, render_export_env=False, render_load_env=False):
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
    finally:
        env.close()

    try:
        print("===== Start restoring =====")
        env = WaymoEnv(
            dict(
                agent_policy=WaymoReplayEgoCarPolicy,
                waymo_data_directory=dir,
                use_render=render_load_env,
                case_num=scenario_num
            )
        )
        scenarios_restored = env.export_scenarios(policy, scenario_index=[i for i in range(scenario_num)], verbose=True)

    finally:
        env.close()
        # if dir is not None:
        #     shutil.rmtree(dir)

    assert_scenario_equal(scenarios, scenarios_restored, only_compare_sdc=True)


if __name__ == "__main__":
    test_export_metadrive_scenario_reproduction(scenario_num=10)
    test_export_metadrive_scenario_easy(scenario_num=10, render_export_env=False, render_load_env=False)
    test_export_metadrive_scenario_hard(scenario_num=10, render_export_env=False, render_load_env=False)
    # WIP_test_export_waymo_scenario(scenario_num=1, render_export_env=False, render_load_env=False)
