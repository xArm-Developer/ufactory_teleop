# UFACTORY Teleoperation System

This project provides teleoperation solutions for UFACTORY robotic arms, featuring two independent approaches:

1. **Pika Sense-based Teleoperation**: Utilizing Agilex Robotics' Pika Sense technology for precise motion tracking and control
[![Watch the video](assets/pika_teleoperation_system.jpg)](https://www.youtube.com/watch?v=D4L1dyyBriA)
2. **GELLO-inspired Framework**: Based on concepts from the open-source GELLO framework (https://wuphilipp.github.io/gello_site/)

## Overview

The UFACTORY Teleoperation System enables intuitive remote control of UFACTORY robotic arms through advanced motion tracking technologies. These systems are designed to lower the barrier to collecting high-quality demonstration data for robotic learning and manipulation tasks.

## Teleoperation Solutions

### Pika Sense-based Solution
- Utilizes Agilex Robotics' Pika Sense for precise motion tracking and control
- Enables real-time teleoperation with minimal latency
- Supports positional and rotational tracking
- Ideal for applications requiring high-fidelity motion capture

### GELLO-inspired Solution
- Incorporates concepts from GELLO, a low-cost, intuitive teleoperation framework for robot manipulators
- Designed to be user-friendly and affordable, using off-the-shelf components
- Provides kinematically equivalent control for more intuitive operation
- Suitable for educational purposes and rapid prototyping

## Features

- **Intuitive Control**: Direct manipulation interfaces that reduce the gap between user and robot embodiment
- **Cost-Effective Solutions**: Leverages commercially available tracking technologies
- **High-Quality Demonstrations**: Enables collection of precise demonstration data for imitation learning
- **Multi-Robot Support**: Compatible with various UFACTORY robotic arm models (xArm 5/6/7, Lite 6, 850)

## Getting Started

For detailed installation instructions, system requirements, and usage guidelines for the Pika Sense-based solution, please refer to the comprehensive documentation in the [pika_teleop/readme.md](pika_teleop/readme.md) file.

## References

- [Agilex Robotics Pika Sense](https://global.agilex.ai/products/pika)
- [UFACTORY Robotic Arms](https://www.ufactory.cc/xarm-collaborative-robot/)
- [GELLO: General Low-Cost Teleoperation Framework](https://wuphilipp.github.io/gello_site/)