from blade_client_reporter import get_reporter
import lightbox_pyblish_gui

# Launch Pyblish GUI inside Maya
lightbox_pyblish_gui.start_lightbox_pyblish_gui(
    config_name="cgm_maya_pyblish_plugins",
    set_name="场景移动端",
    window_title="Cgm Check Toolkit",
    hosts=["maya"],
)

# Send a simple analytic/reporting event
with get_reporter(app_name="cgm_maya_shelf", browser_name="maya") as api:
    api.report_count(event_name="start", action="init a setup.", tool_name="pyblish")