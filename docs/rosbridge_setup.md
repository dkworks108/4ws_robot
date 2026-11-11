# Rosbridge & Web Streaming Configuration Guide
## Four-Wheel Steering Mobile Robot (Project 04)

### 1. Overview

Communication between the web browser and ROS 2 Humble relies on two robust server components:
1. **`rosbridge_server` (Port 9090):** Provides a JSON-based WebSocket API for subscribing to topics, publishing velocity commands, calling services, and dispatching Nav2 action goals.
2. **`web_video_server` (Port 8080):** Provides efficient HTTP MJPEG video streaming for ROS 2 camera image topics (`sensor_msgs/Image`).

---

### 2. Rosbridge WebSocket Configuration

The Rosbridge server is configured and launched via `four_wheel_mobile_control/launch/mobile_control.launch.py`:

```python
rosbridge_node = Node(
    package='rosbridge_server',
    executable='rosbridge_websocket',
    name='rosbridge_websocket',
    output='screen',
    parameters=[{
        'port': 9090,
        'address': '0.0.0.0',
        'call_services_in_new_thread': True,
        'send_action_goals_in_new_thread': True,
        'default_call_service_timeout': 5.0,
        'use_sim_time': use_sim_time
    }]
)
```

#### Key Rosbridge Features Leveraged:
- **`rosapi` Service Reflection:** The companion `rosapi_node` allows browser clients to dynamically inspect topic types and active services without pre-compiling message schemas in JavaScript.
- **Multithreaded Service Calls:** Setting `call_services_in_new_thread: True` prevents synchronous service calls from blocking telemetry streaming.
- **Action Server Integration:** Setting `send_action_goals_in_new_thread: True` enables non-blocking Nav2 `navigate_to_pose` execution.

---

### 3. Web Video Server Configuration

The `web_video_server` streams the robot's onboard pinhole RGB camera directly to standard HTML `<img>` elements without requiring complex WebRTC signaling servers:

```python
web_video_node = Node(
    package='web_video_server',
    executable='web_video_server',
    name='web_video_server',
    output='screen',
    parameters=[{
        'port': 8080,
        'address': '0.0.0.0',
        'use_sim_time': use_sim_time
    }]
)
```

#### Client Request URL Pattern:
```html
<img src="http://<ROBOT_IP>:8080/stream?topic=/camera/image_raw&type=mjpeg&width=640&height=480&quality=80" />
```

---

### 4. Security & Network Considerations

- **Private LAN Binding:** By default, servers bind to `0.0.0.0` to permit connections from smartphones on the same Wi-Fi router.
- **Firewall Exceptions:** Ensure ports 3000 (HTTP Web), 8080 (Video), and 9090 (WebSocket) are open:
  ```bash
  sudo ufw allow 3000/tcp
  sudo ufw allow 8080/tcp
  sudo ufw allow 9090/tcp
  ```
- **Public Internet Warning:** Never expose Rosbridge (Port 9090) directly to the public internet without an authenticating reverse proxy (e.g. Nginx with WSS SSL/TLS and token authorization).

