tell application "System Events"
	activate
	display dialog "欢迎使用 Compositor 一键中文汉化补丁！" & return & return & "• 标准：严格对照 Adobe Photoshop 官方简体中文版" & return & "• 特性：零源码破坏、三重复合防御引擎、完全彻底汉化" with title "Compositor 一键汉化补丁" buttons {"取消", "立即汉化"} default button "立即汉化" with icon note
end tell

set buttonPressed to button returned of result
if buttonPressed is "立即汉化" then
	set targetAppPath to "/Applications/Compositor.app"
	tell application "Finder"
		set appExists to exists POSIX file targetAppPath
	end tell
	
	if not appExists then
		display dialog "未在【应用程序】中找到 Compositor.app！" & return & return & "请先从 GitHub 或 Homebrew 安装 Compositor，然后再运行本补丁。" with title "未找到目标应用" buttons {"好"} default button "好" with icon stop
		return
	end if
	
	-- 获取自身路径并定位自包含 payload 脚本
	set appBundlePath to POSIX path of (path to me)
	set internalScript to appBundlePath & "Contents/Resources/payload/install_plugin.py"
	
	set scriptPath to ""
	tell application "Finder"
		if exists POSIX file internalScript then
			set scriptPath to internalScript
		end if
	end tell
	
	-- 降级查找同级目录或上级工程目录
	if scriptPath is "" then
		tell application "Finder"
			set appParentDir to POSIX path of ((container of (path to me)) as alias)
			set peerScript to appParentDir & "install_plugin.py"
			if exists POSIX file peerScript then
				set scriptPath to peerScript
			end if
		end tell
	end if
	
	if scriptPath is "" then
		set fallbackScript to "/Users/hansonwang/Documents/PS-Compositor/plugin/CompositorZH/Scripts/install_plugin.py"
		tell application "Finder"
			if exists POSIX file fallbackScript then
				set scriptPath to fallbackScript
			end if
		end tell
	end if
	
	if scriptPath is "" then
		display dialog "未找到汉化安装脚本核心组件！" & return & return & "请确认安装包完整。" with title "错误" buttons {"好"} default button "好" with icon stop
		return
	end if
	
	try
		do shell script "python3 " & quoted form of scriptPath & " --app " & quoted form of targetAppPath
		tell application "System Events"
			activate
			display dialog "🎉 恭喜！Compositor 汉化补丁已成功安装生效！" & return & return & "已为您自动启动 Compositor，尽享全中文专业修图体验。" with title "汉化完成" buttons {"完成"} default button "完成" with icon note
		end tell
		do shell script "open " & quoted form of targetAppPath
	on error errMsg
		display dialog "安装遇到问题：" & return & errMsg with title "错误" buttons {"好"} default button "好" with icon caution
	end try
end if
