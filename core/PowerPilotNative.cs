using System;
using System.IO;
using System.Text;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Collections.Generic;
using Microsoft.Win32;
using System.ServiceProcess;
using System.Management;

namespace PowerPilotNative
{
    [StructLayout(LayoutKind.Sequential)]
    public struct SYSTEM_POWER_STATUS
    {
        public byte ACLineStatus;
        public byte BatteryFlag;
        public byte BatteryLifePercent;
        public byte SystemStatusFlag;
        public int BatteryLifeTime;
        public int BatteryFullLifeTime;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT
    {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    public class Program
    {
        [DllImport("kernel32.dll", SetLastError = true)]
        public static extern bool GetSystemPowerStatus(out SYSTEM_POWER_STATUS lpSystemPowerStatus);

        [DllImport("powrprof.dll", SetLastError = true)]
        public static extern uint PowerGetActiveScheme(IntPtr UserRootPowerKey, out IntPtr ActivePolicyGuid);

        [DllImport("powrprof.dll", SetLastError = true)]
        public static extern uint PowerSetActiveScheme(IntPtr UserPowerKey, ref Guid SchemeGuid);

        [DllImport("powrprof.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        public static extern uint PowerReadFriendlyName(IntPtr RootPowerKey, ref Guid SchemeGuid, IntPtr SubGroupOfPowerSettingsGuid, IntPtr PowerSettingGuid, StringBuilder Buffer, ref uint BufferSize);

        [DllImport("user32.dll")]
        public static extern bool EnumDesktopWindows(IntPtr hDesktop, EnumWindowsProc lpfn, IntPtr lParam);

        [DllImport("user32.dll")]
        public static extern bool IsWindowVisible(IntPtr hWnd);

        [DllImport("user32.dll", SetLastError = true)]
        public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

        [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
        public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

        [DllImport("user32.dll", SetLastError = true)]
        public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);

        public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

        static int Main(string[] args)
        {
            if (args.Length == 0)
            {
                Console.WriteLine("{\"status\":\"ok\",\"engine\":\"PowerPilotNative\",\"version\":\"2.0\"}");
                return 0;
            }

            string command = args[0].ToLowerInvariant();
            try
            {
                switch (command)
                {
                    case "battery":
                        GetBatteryStatus();
                        break;
                    case "power-plan":
                        GetActivePowerPlan();
                        break;
                    case "set-plan":
                        if (args.Length > 1)
                            SetPowerPlan(args[1]);
                        else
                            Console.WriteLine("{\"error\":\"Missing plan GUID\"}");
                        break;
                    case "notifications":
                        if (args.Length > 1)
                            SetNotifications(args[1].ToLowerInvariant() == "enable");
                        else
                            GetNotifications();
                        break;
                    case "active-windows":
                        GetActiveWindows();
                        break;
                    case "brightness":
                        if (args.Length > 1)
                        {
                            int val;
                            if (int.TryParse(args[1], out val))
                                SetBrightness(val);
                            else
                                Console.WriteLine("{\"error\":\"Invalid brightness value\"}");
                        }
                        else
                        {
                            GetBrightness();
                        }
                        break;
                    case "service":
                        if (args.Length > 2)
                            ManageService(args[1], args[2]);
                        else if (args.Length > 1)
                            ManageService(args[1], "status");
                        else
                            Console.WriteLine("{\"error\":\"Missing service name\"}");
                        break;
                    case "kill-pids":
                        if (args.Length > 1)
                            KillPids(args[1]);
                        else
                            Console.WriteLine("{\"killed\":0}");
                        break;
                    default:
                        Console.WriteLine("{\"error\":\"Unknown command: " + command + "\"}");
                        return 1;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine("{\"error\":\"" + EscapeJson(ex.Message) + "\"}");
                return 1;
            }
            return 0;
        }

        static void GetBatteryStatus()
        {
            SYSTEM_POWER_STATUS status;
            bool ok = GetSystemPowerStatus(out status);
            if (!ok)
            {
                Console.WriteLine("{\"available\":false,\"error\":\"Failed to get system power status\"}");
                return;
            }

            bool plugged = status.ACLineStatus == 1;
            int percent = (int)status.BatteryLifePercent;
            int timeLeft = status.BatteryLifeTime;
            string statusStr;
            if (plugged)
                statusStr = percent >= 100 ? "Fully Charged" : "Charging";
            else
                statusStr = "On Battery";

            long designedCap = 0;
            long fullCap = 0;
            double healthPct = 100.0;
            bool healthAvailable = false;

            try
            {
                using (var searcher = new ManagementObjectSearcher("root\\wmi", "SELECT DesignedCapacity FROM BatteryStaticData"))
                {
                    foreach (ManagementObject obj in searcher.Get())
                    {
                        var val = obj["DesignedCapacity"];
                        if (val != null)
                        {
                            designedCap = Convert.ToInt64(val);
                            break;
                        }
                    }
                }

                using (var searcher = new ManagementObjectSearcher("root\\wmi", "SELECT FullChargedCapacity FROM BatteryFullChargedCapacity"))
                {
                    foreach (ManagementObject obj in searcher.Get())
                    {
                        var val = obj["FullChargedCapacity"];
                        if (val != null)
                        {
                            fullCap = Convert.ToInt64(val);
                            break;
                        }
                    }
                }

                if (designedCap > 0 && fullCap > 0)
                {
                    healthPct = Math.Round(((double)fullCap / (double)designedCap) * 100.0, 1);
                    if (healthPct > 100.0) healthPct = 100.0;
                    healthAvailable = true;
                }
            }
            catch {}

            string timeStr;
            if (plugged)
                timeStr = "Plugged In";
            else if (timeLeft == -1 || timeLeft > 86400)
                timeStr = "Calculating...";
            else
            {
                int h = timeLeft / 3600;
                int m = (timeLeft % 3600) / 60;
                timeStr = h + "h " + m + "m";
            }

            StringBuilder sb = new StringBuilder();
            sb.Append("{");
            sb.Append("\"available\":true,");
            sb.Append("\"percent\":" + (percent <= 100 ? percent : 0) + ",");
            sb.Append("\"plugged\":" + (plugged ? "true" : "false") + ",");
            sb.Append("\"time_left\":\"" + timeStr + "\",");
            sb.Append("\"time_left_seconds\":" + timeLeft + ",");
            sb.Append("\"status\":\"" + statusStr + "\",");
            sb.Append("\"health\":{");
            sb.Append("\"available\":" + (healthAvailable ? "true" : "false") + ",");
            sb.Append("\"health_percent\":" + healthPct.ToString("0.0", System.Globalization.CultureInfo.InvariantCulture) + ",");
            sb.Append("\"designed_capacity_mwh\":" + designedCap + ",");
            sb.Append("\"full_charge_capacity_mwh\":" + fullCap);
            sb.Append("}");
            sb.Append("}");
            Console.WriteLine(sb.ToString());
        }

        static void GetActivePowerPlan()
        {
            IntPtr ptr;
            uint res = PowerGetActiveScheme(IntPtr.Zero, out ptr);
            if (res != 0 || ptr == IntPtr.Zero)
            {
                Console.WriteLine("{\"guid\":\"\",\"name\":\"Unknown\"}");
                return;
            }

            Guid schemeGuid = (Guid)Marshal.PtrToStructure(ptr, typeof(Guid));
            Marshal.FreeHGlobal(ptr);

            uint bufferSize = 256;
            StringBuilder nameBuf = new StringBuilder((int)bufferSize);
            PowerReadFriendlyName(IntPtr.Zero, ref schemeGuid, IntPtr.Zero, IntPtr.Zero, nameBuf, ref bufferSize);

            string name = nameBuf.ToString();
            if (string.IsNullOrEmpty(name)) name = "Power Plan";

            Console.WriteLine("{\"guid\":\"" + schemeGuid.ToString() + "\",\"name\":\"" + EscapeJson(name) + "\"}");
        }

        static void SetPowerPlan(string guidStr)
        {
            Guid guid;
            if (!Guid.TryParse(guidStr, out guid))
            {
                Console.WriteLine("{\"success\":false,\"error\":\"Invalid GUID format\"}");
                return;
            }

            uint res = PowerSetActiveScheme(IntPtr.Zero, ref guid);
            Console.WriteLine("{\"success\":" + (res == 0 ? "true" : "false") + ",\"code\":" + res + "}");
        }

        static void GetNotifications()
        {
            try
            {
                using (var key = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Notifications\Settings", false))
                {
                    if (key != null)
                    {
                        object val = key.GetValue("NOC_GLOBAL_SETTING_TOASTS_ENABLED");
                        if (val != null && Convert.ToInt32(val) == 0)
                        {
                            Console.WriteLine("{\"enabled\":false}");
                            return;
                        }
                    }
                }
                Console.WriteLine("{\"enabled\":true}");
            }
            catch
            {
                Console.WriteLine("{\"enabled\":true}");
            }
        }

        static void SetNotifications(bool enable)
        {
            try
            {
                using (var key = Registry.CurrentUser.CreateSubKey(@"Software\Microsoft\Windows\CurrentVersion\Notifications\Settings"))
                {
                    if (key != null)
                    {
                        key.SetValue("NOC_GLOBAL_SETTING_TOASTS_ENABLED", enable ? 1 : 0, RegistryValueKind.DWord);
                        Console.WriteLine("{\"success\":true,\"enabled\":" + (enable ? "true" : "false") + "}");
                        return;
                    }
                }
                Console.WriteLine("{\"success\":false,\"error\":\"Could not open registry key\"}");
            }
            catch (Exception ex)
            {
                Console.WriteLine("{\"success\":false,\"error\":\"" + EscapeJson(ex.Message) + "\"}");
            }
        }

        static void GetActiveWindows()
        {
            var activeWindows = new Dictionary<uint, string>();
            EnumDesktopWindows(IntPtr.Zero, (hWnd, lParam) =>
            {
                if (IsWindowVisible(hWnd))
                {
                    RECT rect;
                    if (GetWindowRect(hWnd, out rect))
                    {
                        int w = rect.Right - rect.Left;
                        int h = rect.Bottom - rect.Top;
                        if (w > 16 && h > 16)
                        {
                            StringBuilder title = new StringBuilder(512);
                            int len = GetWindowText(hWnd, title, title.Capacity);
                            if (len > 0)
                            {
                                string t = title.ToString().Trim();
                                if (!string.IsNullOrEmpty(t) && t != "Program Manager" && t != "Default IME" && t != "MSCTFIME UI")
                                {
                                    uint pid;
                                    GetWindowThreadProcessId(hWnd, out pid);
                                    if (pid > 0 && !activeWindows.ContainsKey(pid))
                                    {
                                        activeWindows[pid] = t;
                                    }
                                }
                            }
                        }
                    }
                }
                return true;
            }, IntPtr.Zero);

            StringBuilder sb = new StringBuilder();
            sb.Append("{\"active_windows\":{");
            bool first = true;
            foreach (var kvp in activeWindows)
            {
                if (!first) sb.Append(",");
                sb.Append("\"" + kvp.Key + "\":\"" + EscapeJson(kvp.Value) + "\"");
                first = false;
            }
            sb.Append("}}");
            Console.WriteLine(sb.ToString());
        }

        static void GetBrightness()
        {
            try
            {
                using (var searcher = new ManagementObjectSearcher("root\\wmi", "SELECT CurrentBrightness FROM WmiMonitorBrightness"))
                {
                    foreach (ManagementObject obj in searcher.Get())
                    {
                        var val = obj["CurrentBrightness"];
                        if (val != null)
                        {
                            Console.WriteLine("{\"brightness\":" + Convert.ToInt32(val) + "}");
                            return;
                        }
                    }
                }
            }
            catch {}
            Console.WriteLine("{\"brightness\":-1}");
        }

        static void SetBrightness(int targetLevel)
        {
            targetLevel = Math.Max(0, Math.Min(100, targetLevel));
            bool success = false;
            try
            {
                using (var searcher = new ManagementObjectSearcher("root\\wmi", "SELECT * FROM WmiMonitorBrightnessMethods"))
                {
                    foreach (ManagementObject obj in searcher.Get())
                    {
                        obj.InvokeMethod("WmiSetBrightness", new object[] { 1, (byte)targetLevel });
                        success = true;
                        break;
                    }
                }
            }
            catch {}
            Console.WriteLine("{\"success\":" + (success ? "true" : "false") + ",\"brightness\":" + targetLevel + "}");
        }

        static void ManageService(string serviceName, string action)
        {
            action = action.ToLowerInvariant();
            try
            {
                using (var sc = new ServiceController(serviceName))
                {
                    if (action == "status")
                    {
                        string statusStr = sc.Status.ToString();
                        Console.WriteLine("{\"service\":\"" + EscapeJson(serviceName) + "\",\"status\":\"" + statusStr + "\",\"running\":" + (sc.Status == ServiceControllerStatus.Running ? "true" : "false") + "}");
                        return;
                    }
                    else if (action == "stop")
                    {
                        if (sc.Status != ServiceControllerStatus.Stopped && sc.Status != ServiceControllerStatus.StopPending)
                        {
                            sc.Stop();
                            sc.WaitForStatus(ServiceControllerStatus.Stopped, TimeSpan.FromSeconds(3));
                        }
                        Console.WriteLine("{\"success\":true,\"service\":\"" + EscapeJson(serviceName) + "\",\"action\":\"stopped\"}");
                        return;
                    }
                    else if (action == "start")
                    {
                        if (sc.Status != ServiceControllerStatus.Running && sc.Status != ServiceControllerStatus.StartPending)
                        {
                            sc.Start();
                            sc.WaitForStatus(ServiceControllerStatus.Running, TimeSpan.FromSeconds(3));
                        }
                        Console.WriteLine("{\"success\":true,\"service\":\"" + EscapeJson(serviceName) + "\",\"action\":\"started\"}");
                        return;
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine("{\"success\":false,\"service\":\"" + EscapeJson(serviceName) + "\",\"error\":\"" + EscapeJson(ex.Message) + "\"}");
            }
        }

        static void KillPids(string pidListStr)
        {
            int killed = 0;
            string[] parts = pidListStr.Split(new char[] { ',', ';' }, StringSplitOptions.RemoveEmptyEntries);
            foreach (string part in parts)
            {
                int pid;
                if (int.TryParse(part.Trim(), out pid))
                {
                    try
                    {
                        Process proc = Process.GetProcessById(pid);
                        proc.Kill();
                        killed++;
                    }
                    catch {}
                }
            }
            Console.WriteLine("{\"killed\":" + killed + "}");
        }

        static string EscapeJson(string s)
        {
            if (string.IsNullOrEmpty(s)) return "";
            return s.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\r", "").Replace("\n", " ");
        }
    }
}
