"""Sanity check before a long run: JAX sees the GPU and SAPIEN can render a SIMPLER scene.

  python env/check_gpu.py

SIMPLER renders with Vulkan. If the render step fails or is very slow (hundreds of ms),
check that the NVIDIA Vulkan ICD is installed (/usr/share/vulkan/icd.d/nvidia_icd.json)
and that SAPIEN did not fall back to the CPU renderer (llvmpipe).
"""
import time

import jax

print("jax devices:", jax.devices())
assert any(d.platform == "gpu" for d in jax.devices()), "JAX does not see a GPU"

import simpler_env  # noqa: E402
from simpler_env.utils.env.observation_utils import get_image_from_maniskill2_obs_dict  # noqa: E402

env = simpler_env.make("widowx_carrot_on_plate")
obs, _ = env.reset(seed=0)
img = get_image_from_maniskill2_obs_dict(env, obs)
print("image:", img.shape, img.dtype)

ts = []
for _ in range(10):
    t = time.time()
    obs, *_ = env.step(env.action_space.sample())
    ts.append(time.time() - t)
print(f"env.step incl. render: median {1000 * sorted(ts)[5]:.1f} ms")
env.close()
print("OK")
