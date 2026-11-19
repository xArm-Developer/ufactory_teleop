"""Platform-specific wheel tag: uf_teleop_core bundles Linux .so files under devices/umi/xvlib."""
from setuptools import Distribution, setup
from wheel.bdist_wheel import bdist_wheel


class BinaryDistribution(Distribution):
    def has_ext_modules(self):
        return True


class PlatformWheel(bdist_wheel):
    def get_tag(self):
        _, _, platform = super().get_tag()
        return 'py3', 'none', platform


setup(distclass=BinaryDistribution, cmdclass={'bdist_wheel': PlatformWheel})
