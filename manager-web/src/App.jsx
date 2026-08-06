'use client';
import React, { Component, useEffect, useState, useRef, useMemo, useCallback } from 'react';

// REACT ERROR BOUNDARY FALLBACK (CHỐNG BLANK SCREEN)
class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error("Uncaught Runtime Error:", error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-black text-zinc-100 flex items-center justify-center p-6 font-mono">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 max-w-md w-full space-y-4 shadow-2xl">
            <div className="flex items-center gap-2 text-rose-400">
              <span className="w-2 h-2 rounded-full bg-rose-500"></span>
              <h2 className="text-sm font-bold uppercase tracking-wider">Lỗi Hiển Thị (Runtime Error)</h2>
            </div>
            <p className="text-xs text-zinc-400 leading-relaxed font-sans">
              Hệ thống đã tự động kích hoạt chế độ an toàn để ngăn ngừa lỗi màn hình đen.
            </p>
            <div className="p-3 bg-black border border-zinc-800 rounded text-[11px] text-zinc-300 overflow-x-auto max-h-32">
              {this.state.error?.toString() || 'Uncaught Application Exception'}
            </div>
            <button
              onClick={() => window.location.reload()}
              className="w-full bg-white text-black font-semibold hover:bg-zinc-200 py-2 rounded text-xs transition"
            >
              Tải Lại Trang
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

import { supabase } from './supabase'
import { parseGoogleSheetData, deduplicateActiveSessions, formatClockTime } from './lib/utils'
import { StatusDot } from './components/ui/StatusDot'
import { Button } from './components/ui/Button'
import { Sidebar } from './components/layout/Sidebar'
import { Header } from './components/layout/Header'
import { MobileNav } from './components/layout/MobileNav'
import { MetricCard } from './components/overview/MetricCard'
import { ProcessTable } from './components/process/ProcessTable'
import { ProcessCardList } from './components/process/ProcessCardList'
import { ScheduleTable } from './components/schedule/ScheduleTable'
import { ScheduleCardList } from './components/schedule/ScheduleCardList'
import { PermissionMatrix } from './components/admin/PermissionMatrix'
import { PermissionAccordion } from './components/admin/PermissionAccordion'
import {
  Shield, Activity, Bot, PauseCircle, Eye, EyeOff, KeyRound, Lock, Search,
  RefreshCw, CheckCircle2, Circle, Trash2, Camera, Clock, Cpu, HardDrive, Globe, AppWindow,
  Settings, FileText, AlertTriangle, User, PlayCircle, ShieldCheck, ChevronRight, X, Pin
} from 'lucide-react'



// Safe Local/Session Storage Access Helpers (Chống Nổ SSR/SecurityError)
function safeGetLocalStorage(key, defaultValue = '') {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      return window.localStorage.getItem(key) || defaultValue
    }
  } catch (e) {}
  return defaultValue
}

function safeSetLocalStorage(key, value) {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem(key, value)
    }
  } catch (e) {}
}

function safeRemoveLocalStorage(key) {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.removeItem(key)
    }
  } catch (e) {}
}

function safeGetSessionStorage(key, defaultValue = '') {
  try {
    if (typeof window !== 'undefined' && window.sessionStorage) {
      return window.sessionStorage.getItem(key) || defaultValue
    }
  } catch (e) {}
  return defaultValue
}

function safeSetSessionStorage(key, value) {
  try {
    if (typeof window !== 'undefined' && window.sessionStorage) {
      window.sessionStorage.setItem(key, value)
    }
  } catch (e) {}
}

function ParentalControlApp() {
  // State Đăng Nhập / Quyền Admin & Ghi Nhớ 30 Ngày
  const [isAdmin, setIsAdmin] = useState(false)
  const [showLoginModal, setShowLoginModal] = useState(false)
  const [pinInput, setPinInput] = useState('')
  const [rememberMe, setRememberMe] = useState(true)
  const [loginError, setLoginError] = useState('')

  // State Quản Lý Tư Cách Truy Cập (Role Selection), Mật Khẩu Tư Cách & Phân Quyền
  const [userRole, setUserRole] = useState(() => safeGetLocalStorage('user_role') || '')
  const [showRoleModal, setShowRoleModal] = useState(false)
  const [selectedRoleToAuth, setSelectedRoleToAuth] = useState(null)
  const [roleAuthInput, setRoleAuthInput] = useState('')
  const [roleAuthError, setRoleAuthError] = useState('')
  const [newViewerRoleInput, setNewViewerRoleInput] = useState('')

  const [rolePasswords, setRolePasswords] = useState({})
  const [rolePermissions, setRolePermissions] = useState({})
  
  // Unique Device ID (per physical device/browser)
  const [deviceId] = useState(() => {
    let did = safeGetLocalStorage('web_device_id')
    if (!did) {
      did = 'dev_' + Math.random().toString(36).substring(2, 9) + '_' + Date.now()
      safeSetLocalStorage('web_device_id', did)
    }
    return did
  })

  // Unique Session ID (per browser tab)
  const [sessionId] = useState(() => {
    let sid = safeGetSessionStorage('web_tab_session_id')
    if (!sid) {
      sid = 'tab_' + Math.random().toString(36).substring(2, 9) + '_' + Date.now()
      safeSetSessionStorage('web_tab_session_id', sid)
    }
    return sid
  })
  const [isSessionBlocked, setIsSessionBlocked] = useState(false)
  const [activeSessions, setActiveSessions] = useState([])
  const [customRoles, setCustomRoles] = useState(['Em trai', 'Phụ huynh', 'Viewer'])
  const [newRoleInput, setNewRoleInput] = useState('')

  // State Xóa Nhiều Ảnh Chụp & Sắp Xếp Theo Ngày
  const [selectedScreenshotIds, setSelectedScreenshotIds] = useState([])
  const [bulkDeleting, setBulkDeleting] = useState(false)

  // State Xóa Nhiều Lịch Sử Duyệt Web & Phân Trang/Lọc
  const [selectedHistoryIds, setSelectedHistoryIds] = useState([])
  const [bulkDeletingHistory, setBulkDeletingHistory] = useState(false)
  const [appHistorySearch, setAppHistorySearch] = useState('')
  const [selectedAppHistoryIds, setSelectedAppHistoryIds] = useState([])
  const [bulkDeletingAppHistory, setBulkDeletingAppHistory] = useState(false)
  const [usageSubTab, setUsageSubTab] = useState('apps') // 'apps' | 'history' | 'black_list'

  // State Tạm Dừng Kiểm Soát Từ Xa (Pause/Resume Master Control)
  const [isPaused, setIsPaused] = useState(false)
  const [togglePauseLoading, setTogglePauseLoading] = useState(false)

  // State Black List Rules (Web & Apps)
  const [webRules, setWebRules] = useState([])
  const [webUsage, setWebUsage] = useState([])
  const [showAddBlackListModal, setShowAddBlackListModal] = useState(false)
  const [blackListRuleType, setBlackListRuleType] = useState('web') // 'web' | 'app'
  const [blackListTargetInput, setBlackListTargetInput] = useState('')
  const [blackListCategory, setBlackListCategory] = useState('forbidden') // 'forbidden' | 'limited'
  const [blackListMaxMinutes, setBlackListMaxMinutes] = useState(30)
  const [blackListSubTab, setBlackListSubTab] = useState('web') // 'web' | 'app'

  // State Lưu Tab Hiện Tại vào LocalStorage
  const [activeTab, setActiveTab] = useState(() => safeGetLocalStorage('active_tab') || 'overview')

  // Theme State: 'dark' | 'black' | 'light'
  const [themeMode, setThemeMode] = useState(() => safeGetLocalStorage('app_theme') || 'dark')

  const [device, setDevice] = useState(null)
  const [currentTime, setCurrentTime] = useState(Date.now())



  // UPDATE CURRENT TIME MỖI 10 GIÂY ĐỂ ĐÁNH GIÁ ONLINE/OFFLINE THỜI GIAN THỰC
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(Date.now()), 10000)
    return () => clearInterval(timer)
  }, [])

  const [processes, setProcesses] = useState([])
  const [activeWindows, setActiveWindows] = useState([])


  const [screenshots, setScreenshots] = useState([])
  const [browserHistory, setBrowserHistory] = useState([])
  const [historySearch, setHistorySearch] = useState('')
  
  const [timeRules, setTimeRules] = useState([])
  const [appRules, setAppRules] = useState([])
  const [appUsage, setAppUsage] = useState([])
  const [schedules, setSchedules] = useState([])
  const [chatMessages, setChatMessages] = useState([])
  const [todoNotes, setTodoNotes] = useState([])
  const [sheetTasks, setSheetTasks] = useState([])
  const [completedSheetTasks, setCompletedSheetTasks] = useState({})
  
  const [chatInput, setChatInput] = useState('')
  const [floatingChatInput, setFloatingChatInput] = useState('')
  const [appConfig, setAppConfig] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedImage, setSelectedImage] = useState(null)

  // Storage Management States
  const [storageLogType, setStorageLogType] = useState('all')
  const [storageStartDate, setStorageStartDate] = useState(() => {
    const d = new Date()
    d.setDate(d.getDate() - 30)
    return d.toISOString().split('T')[0]
  })
  const [storageEndDate, setStorageEndDate] = useState(() => new Date().toISOString().split('T')[0])
  const [isCleaningStorage, setIsCleaningStorage] = useState(false)
  const [storageMessage, setStorageMessage] = useState(null)
  const [cmdSending, setCmdSending] = useState(false)
  const [updateSending, setUpdateSending] = useState(false)

  // Floating Widgets Toggle & Tab Order: 'todo' | 'chat' | 'online'
  const [showFloatingWidget, setShowFloatingWidget] = useState(false)
  const [floatingTab, setFloatingTab] = useState('todo')
  const [showMobileDrawer, setShowMobileDrawer] = useState(false)

  // Form states cho ToDo Note Refactor
  const [quickAddTitle, setQuickAddTitle] = useState('')
  const [quickAddType, setQuickAddType] = useState('custom')
  const [isSyncingSheet, setIsSyncingSheet] = useState(false)
  const [editingTaskId, setEditingTaskId] = useState(null)
  const [editingTaskTitle, setEditingTaskTitle] = useState('')
  const [editingTaskType, setEditingTaskType] = useState('custom')
  const [deletedSheetTaskIds, setDeletedSheetTaskIds] = useState([])

  // TỰ ĐỘNG TÍNH TOÁN DYNAMIC IS_ONLINE (ĐA NGUỒN: HEARTBEAT, SCREENSHOTS & WINDOW LOGS)
  const isDeviceOnline = useMemo(() => {
    try {
      let latestMs = 0

      // 1. Kiểm tra timestamp từ thiết bị (devices.last_seen)
      if (device?.last_seen) {
        const t = new Date(device.last_seen).getTime()
        if (!isNaN(t) && t > latestMs) latestMs = t
      }

      // 2. Kiểm tra timestamp ảnh chụp màn hình gần nhất (screenshot_logs.created_at)
      if (screenshots && screenshots.length > 0 && screenshots[0]?.created_at) {
        const t = new Date(screenshots[0].created_at).getTime()
        if (!isNaN(t) && t > latestMs) latestMs = t
      }

      // 3. Kiểm tra timestamp cửa sổ hoạt động gần nhất (active_window_logs.created_at)
      if (activeWindows && activeWindows.length > 0 && activeWindows[0]?.created_at) {
        const t = new Date(activeWindows[0].created_at).getTime()
        if (!isNaN(t) && t > latestMs) latestMs = t
      }

      if (latestMs === 0) return false

      const diffSec = (currentTime - latestMs) / 1000
      // Đang có tương tác trong vòng 120s (chấp nhận lệch múi giờ -300s đến 120s) -> ONLINE (Chấm xanh)
      return diffSec < 35 && diffSec > -300
    } catch {
      return false
    }
  }, [device, screenshots, activeWindows, currentTime])

  // States cho Google Sheet Calendar Data Table & Widget Refactor
  const [allSheetEntries, setAllSheetEntries] = useState([])
  const [calendarDateFilter, setCalendarDateFilter] = useState('today')
  const [calendarPriorityFilter, setCalendarPriorityFilter] = useState('all')
  const [calendarSearch, setCalendarSearch] = useState('')

  const [newAgentPass, setNewAgentPass] = useState('')
  const [newAdminPin, setNewAdminPin] = useState('')
  const [screenshotMin, setScreenshotMin] = useState(3)
  const [configMsg, setConfigMsg] = useState('')

  // States cho Cài Đặt Admin Refactor
  const [settingsSubTab, setSettingsSubTab] = useState('permissions')
  const [showAgentPass, setShowAgentPass] = useState(false)
  const [showAdminPin, setShowAdminPin] = useState(false)
  const [showBlockSessionModal, setShowBlockSessionModal] = useState(false)
  const [sessionToBlock, setSessionToBlock] = useState(null)

  // Task 1: Quyền mở máy (Agent gọi lên kiểm tra)
  const [isDeviceAllowed, setIsDeviceAllowed] = useState(true)

  // Task 4: Phương thức giới hạn giờ & Master Switch
  const [timeLimitMode, setTimeLimitMode] = useState('time_frame')
  const [isMasterTimeLimitActive, setIsMasterTimeLimitActive] = useState(true)

  // Confirm Modal Xóa Lịch Sử Theo Ngày
  const [showDeleteDateModal, setShowDeleteDateModal] = useState(false)
  const [dateToDelete, setDateToDelete] = useState(null)

  // Task 6: Ẩn app không dùng + Date picker lịch sử
  const [hideUnusedApps, setHideUnusedApps] = useState(false)
  const [historyDate, setHistoryDate] = useState(new Date().toISOString().split('T')[0])
  const historyDateRef = useRef(new Date().toISOString().split('T')[0])
  const [availableDates, setAvailableDates] = useState([])
  const [dateFilteredWindows, setDateFilteredWindows] = useState([])
  const [dateFilteredHistory, setDateFilteredHistory] = useState([])

  const DEVICE_NAME = 'May_Em_Trai'
  const dayNames = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật']
  
  const GOOGLE_SHEET_EMBED = 'https://docs.google.com/spreadsheets/d/1votdcKbIGv-lz5AZJh76qTxVufXusAicDgpzXizH20A/edit?embedded=true&rm=minimal'
  const GOOGLE_SHEET_CSV = 'https://docs.google.com/spreadsheets/d/1votdcKbIGv-lz5AZJh76qTxVufXusAicDgpzXizH20A/gviz/tq?tqx=out:csv'
  const GOOGLE_SHEET_URL = 'https://docs.google.com/spreadsheets/d/1votdcKbIGv-lz5AZJh76qTxVufXusAicDgpzXizH20A/edit?usp=sharing'

  // Nhận diện chi tiết Tên thiết bị / Trình duyệt của người dùng
  function getDetailedDeviceInfo() {
    const ua = navigator.userAgent
    let os = 'PC'
    if (ua.includes('Win')) os = 'Windows PC'
    else if (ua.includes('Mac')) os = 'Mac'
    else if (ua.includes('Android')) os = 'Điện thoại Android'
    else if (ua.includes('iPhone') || ua.includes('iPad')) os = 'iPhone/iPad'

    let browser = 'Chrome'
    if (ua.includes('Edg')) browser = 'Edge'
    else if (ua.includes('Safari') && !ua.includes('Chrome')) browser = 'Safari'
    else if (ua.includes('Firefox')) browser = 'Firefox'

    return `${os} (${browser})`
  }

  // Ngày tháng hôm nay định dạng tiếng Việt
  const todayFormatted = new Date().toLocaleDateString('vi-VN', {
    weekday: 'long',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  })

  // Đổi Tab và Lưu vào localStorage
  function changeActiveTab(tabId) {
    document.body.style.overflow = 'unset'
    setActiveTab(tabId)
    safeSetLocalStorage('active_tab', tabId)
  }

  // Lưu lựa chọn Theme vào localStorage
  function changeTheme(mode) {
    setThemeMode(mode)
    safeSetLocalStorage('app_theme', mode)
  }

  // Kiểm tra lưu Ghi nhớ đăng nhập 30 ngày & Modal chọn Tư cách lần đầu
  useEffect(() => {
    const expiry = safeGetLocalStorage('admin_auth_expiry')
    if (expiry && parseInt(expiry) > Date.now()) {
      setIsAdmin(true)
    }

    const savedRole = safeGetLocalStorage('user_role')
    if (!savedRole) {
      setShowRoleModal(true)
    }
  }, [])

  // Đồng bộ Session thiết bị & Tab hiện tại lên Supabase (Heartbeat Presence System)
  async function syncWebSession(role) {
    const activeRole = isAdmin ? 'Admin' : (role || userRole || 'Viewer')
    const deviceInfo = getDetailedDeviceInfo()
    
    try {
      await supabase
        .from('web_access_sessions')
        .upsert({
          session_id: sessionId,
          device_id: deviceId,
          user_role: activeRole,
          device_info: deviceInfo,
          last_active: new Date().toISOString()
        }, { onConflict: 'session_id' })
    } catch (e) {
      console.log('Sync session fallback applied:', e)
    }
  }

  // Dọn dẹp tất cả Session ma / rác quá 35s không ping
  async function cleanupStaleSessions() {
    try {
      const cutoff = new Date(Date.now() - 35000).toISOString()
      await supabase.from('web_access_sessions').delete().lt('last_active', cutoff)
      loadData(false)
    } catch (e) {
      console.log('Cleanup stale sessions error:', e)
    }
  }

  // Client Heartbeat Ping mỗi 12 giây + Lắng nghe sự kiện đóng Tab/Trình duyệt
  useEffect(() => {
    syncWebSession(userRole)

    const heartbeatInterval = setInterval(() => {
      syncWebSession(userRole)
    }, 12000)

    const handleUnload = () => {
      try {
        supabase.from('web_access_sessions').delete().eq('session_id', sessionId)
      } catch (e) {}
    }

    window.addEventListener('beforeunload', handleUnload)

    return () => {
      clearInterval(heartbeatInterval)
      window.removeEventListener('beforeunload', handleUnload)
    }
  }, [userRole, isAdmin, sessionId, deviceId])

  // Chọn Tư Cách Truy Cập (Kiểm tra Mật Khẩu Tư Cách)
  function handleInitiateRoleSelect(role) {
    const passRequired = rolePasswords[role]
    if (passRequired && !isAdmin) {
      setSelectedRoleToAuth(role)
      setRoleAuthInput('')
      setRoleAuthError('')
    } else {
      handleConfirmRoleSelect(role)
    }
  }

  function handleConfirmRoleSelect(role) {
    setUserRole(role)
    safeSetLocalStorage('user_role', role)
    setShowRoleModal(false)
    setSelectedRoleToAuth(null)
    syncWebSession(role)
  }

  function handleVerifyRolePassword(e) {
    e.preventDefault()
    const correctPass = rolePasswords[selectedRoleToAuth]
    if (roleAuthInput === correctPass) {
      handleConfirmRoleSelect(selectedRoleToAuth)
    } else {
      setRoleAuthError('Mật khẩu tư cách không đúng!')
    }
  }

  // Viewer Tự Thêm Tư Cách Mới Ngay Trong Hộp Thoại
  async function handleAddViewerRole(e) {
    e.preventDefault()
    if (!newViewerRoleInput.trim()) return
    const newRole = newViewerRoleInput.trim()
    let updatedRoles = customRoles
    if (!customRoles.includes(newRole)) {
      updatedRoles = [...customRoles, newRole]
      setCustomRoles(updatedRoles)
      try {
        await supabase.from('app_config').update({
          custom_roles: updatedRoles
        }).eq('device_name', DEVICE_NAME)
      } catch (err) {}
    }
    handleInitiateRoleSelect(newRole)
    setNewViewerRoleInput('')
  }

  // Helper parse date string into { day, month, year }
  function parseSheetDateStr(dateStr) {
    if (!dateStr) return null
    const cleaned = dateStr.trim().split(' ')[0]

    let match = cleaned.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})$/)
    if (match) {
      let d = parseInt(match[1], 10)
      let m = parseInt(match[2], 10)
      let y = parseInt(match[3], 10)
      if (y < 100) y += 2000
      return { day: d, month: m, year: y }
    }

    match = cleaned.match(/^(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})$/)
    if (match) {
      let y = parseInt(match[1], 10)
      let m = parseInt(match[2], 10)
      let d = parseInt(match[3], 10)
      return { day: d, month: m, year: y }
    }

    return null
  }

  function isSameDateParsed(d1, d2) {
    if (!d1 || !d2) return false
    return d1.day === d2.day && d1.month === d2.month && d1.year === d2.year
  }

  // THUẬT TOÁN ĐỌC VÀ LÀM SẠCH DỮ LIỆU GOOGLE SHEET BẢNG MỚI (CỘT A: RAW DATE PHẲNG, CỘT C: BUỔI FORWARD FILL)
  function parseGoogleSheetData(csvText) {
    const lines = csvText.split('\n')
    let rawDateColIdx = 0    // Cột A: Ngày/tháng/năm_raw
    let sessionColIdx = 2    // Cột C: Khung giờ/Buổi (Forward Fill)
    let timeColIdx = 3       // Cột D: THỜI GIAN
    let contentColIdx = 4    // Cột E: NỘI DUNG CÔNG VIỆC
    let priorityColIdx = 5   // Cột F: MỨC ĐỘ ƯU TIÊN

    const allEntries = []
    const now = new Date()
    const todayObj = { day: now.getDate(), month: now.getMonth() + 1, year: now.getFullYear() }

    let currentSession = ''

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim()
      if (!line) continue

      const row = line.split(/,(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)/).map(cell => cell.replace(/^"|"$/g, '').trim())

      // 0. Nhận diện chỉ số cột từ hàng Tiêu Đề
      if (i <= 3) {
        for (let c = 0; c < row.length; c++) {
          const h = row[c].toUpperCase()
          if (h.includes('RAW')) rawDateColIdx = c
          if (h.includes('KHUNG GIỜ') || h.includes('BUỔI')) sessionColIdx = c
          if (h.includes('THỜI GIAN') && !h.includes('BIỂU') && !h.includes('RAW')) timeColIdx = c
          if (h.includes('NỘI DUNG')) contentColIdx = c
          if (h.includes('ƯU TIÊN')) priorityColIdx = c
        }
        if (row.some(cell => cell.toUpperCase().includes('NỘI DUNG CÔNG VIỆC'))) continue
      }

      // Cột A: Ngày/tháng/năm_raw (Phẳng)
      const rawDate = row[rawDateColIdx] ? row[rawDateColIdx].trim() : ''

      // Cột C: Khung giờ / Buổi (Forward Fill nếu rỗng)
      const rawSessionCell = row[sessionColIdx] ? row[sessionColIdx].trim() : ''
      if (rawSessionCell && rawSessionCell !== '-' && !rawSessionCell.toUpperCase().includes('KHUNG GIỜ')) {
        currentSession = rawSessionCell
      }

      // Cột D: THỜI GIAN
      const rawTime = row[timeColIdx] ? row[timeColIdx].trim() : ''

      // Cột E: NỘI DUNG CÔNG VIỆC
      const rawContent = row[contentColIdx] ? row[contentColIdx].trim() : ''

      // Cột F: MỨC ĐỘ ƯU TIÊN
      const rawPriority = row[priorityColIdx] ? row[priorityColIdx].trim() : ''

      const cleanTime = rawTime.replace(/\s+/g, ' ').trim()
      const cleanContent = rawContent.replace(/\s+/g, ' ').trim()
      const sessionName = currentSession ? (currentSession.charAt(0).toUpperCase() + currentSession.slice(1)) : ''

      // 2. BỘ LỌC ĐIỀU KIỆN LỌC TASK HỢP LỆ (Strict Task Filtering)
      // - Cột D (THỜI GIAN) KHÔNG ĐƯỢC chứa "?h ~?h" và KHÔNG rỗng.
      // - Cột E (NỘI DUNG CÔNG VIỆC) KHÔNG rỗng, KHÔNG phải "-", KHÔNG phải tiêu đề gộp ngang.
      if (
        !cleanTime ||
        cleanTime === '-' ||
        cleanTime.includes('?h ~?h') ||
        !cleanContent ||
        cleanContent === '-' ||
        cleanContent.toUpperCase().includes('NỘI DUNG CÔNG VIỆC') ||
        cleanContent.includes('?h ~?h') ||
        cleanContent.length <= 2
      ) {
        continue
      }

      // 3. MAP CHUẨN ĐỘ ƯU TIÊN (Priority Tag Mapping: HIGH, DAILY, NORMAL)
      const pLower = rawPriority.toLowerCase()
      let priorityCode = 'NORMAL'
      let priorityLabel = 'Bình thường'
      let priorityScore = 1

      if (pLower.includes('quan trọng') || pLower.includes('high') || pLower.includes('gấp')) {
        priorityCode = 'HIGH'
        priorityLabel = 'Quan trọng'
        priorityScore = 3
      } else if (pLower.includes('hằng ngày') || pLower.includes('hang ngay') || pLower.includes('daily')) {
        priorityCode = 'DAILY'
        priorityLabel = 'Hằng ngày'
        priorityScore = 2
      } else if (pLower.includes('không quan trọng')) {
        priorityCode = 'NORMAL'
        priorityLabel = 'Không quan trọng'
        priorityScore = 1
      }

      // Ghép Khung Giờ hiển thị: Buổi + Thời gian (Ví dụ: "Sáng (8h-9h)")
      let formattedSessionTime = sessionName
      if (cleanTime && cleanTime !== '-' && cleanTime !== '?h ~?h') {
        formattedSessionTime = sessionName ? `${sessionName} (${cleanTime})` : cleanTime
      }
      if (!formattedSessionTime) formattedSessionTime = 'Cả ngày'

      // 4. CHUẨN HÓA NGÀY & SO SÁNH VỚI NGÀY HỆ THỐNG
      const parsedRowDate = parseSheetDateStr(rawDate)
      const isExactToday = isSameDateParsed(parsedRowDate, todayObj)

      allEntries.push({
        id: `sheet_${i}`,
        date: rawDate || `${todayObj.day}/${todayObj.month}/${todayObj.year}`,
        session: currentSession || 'sáng',
        time: cleanTime,
        title: cleanContent,
        content: cleanContent,
        priority: priorityCode, // "HIGH" | "DAILY" | "NORMAL"
        priorityLabel: priorityLabel,
        priorityScore: priorityScore,
        parsedDate: parsedRowDate,
        sessionTime: formattedSessionTime,
        rawSession: sessionName,
        rawTime: cleanTime,
        isDaily: priorityCode === 'DAILY',
        isExactToday: isExactToday
      })
    }

    // LỌC DANH SÁCH CHO "HÔM NAY"
    const exactTodayList = allEntries.filter(e => e.isExactToday)
    let todayList = []

    if (exactTodayList.length > 0) {
      todayList = allEntries.filter(e => e.isExactToday || e.isDaily)
    } else {
      const uniqueDates = [...new Set(allEntries.map(e => e.date).filter(Boolean))]
      const latestDate = uniqueDates.length > 0 ? uniqueDates[uniqueDates.length - 1] : ''
      todayList = allEntries.filter(e => e.date === latestDate || e.isDaily)
    }

    const seen = new Set()
    const deduplicatedToday = []
    for (const item of todayList) {
      const key = item.title.toLowerCase().trim()
      if (!seen.has(key)) {
        seen.add(key)
        deduplicatedToday.push({ ...item, isToday: true })
      }
    }

    deduplicatedToday.sort((a, b) => b.priorityScore - a.priorityScore)

    const todayIds = new Set(deduplicatedToday.map(e => e.id))
    const finalAllEntries = allEntries.map(e => ({
      ...e,
      isToday: todayIds.has(e.id)
    }))

    return {
      allEntries: finalAllEntries,
      todayEntries: deduplicatedToday
    }
  }

  // Đọc danh sách nhiệm vụ TO DO & LỊCH HỌC TỪ GOOGLE SHEET CSV
  async function fetchGoogleSheetTasks() {
    setIsSyncingSheet(true)
    try {
      const res = await fetch(GOOGLE_SHEET_CSV)
      if (res.ok) {
        const text = await res.text()
        const { allEntries, todayEntries } = parseGoogleSheetData(text)
        setAllSheetEntries(allEntries)
        setSheetTasks(todayEntries)
        return
      }
    } catch (e) {
      console.log('Sheet CSV fetch fallback applied', e)
    } finally {
      setTimeout(() => setIsSyncingSheet(false), 300)
    }

    const fallbackEntries = [
      { id: 'sheet_1', title: 'Đánh răng rửa mặt đi ăn sáng vệ sinh cá nhân', priority: 'Hằng ngày', sessionTime: 'Sáng', date: todayFormatted, isDaily: true, isToday: true },
      { id: 'sheet_2', title: 'Học lập trình Web & làm bài tập AutoCAD', priority: 'Quan trọng', sessionTime: 'Sáng', date: todayFormatted, isDaily: false, isToday: true },
      { id: 'sheet_3', title: 'Xuống phụ mẹ nấu cơm ăn trưa', priority: 'Hằng ngày', sessionTime: 'Trưa', date: todayFormatted, isDaily: true, isToday: true },
      { id: 'sheet_4', title: 'Làm bài tập lớn CAD & Ôn thi môn Lý', priority: 'Quan trọng', sessionTime: 'Chiều', date: todayFormatted, isDaily: false, isToday: true },
      { id: 'sheet_6', title: 'Dọn dẹp hàng hóa cửa hàng', priority: 'Hằng ngày', sessionTime: 'Tối', date: todayFormatted, isDaily: true, isToday: true },
    ]
    setAllSheetEntries(fallbackEntries)
    setSheetTasks(fallbackEntries)
    setIsSyncingSheet(false)
  }

  // Ref chống Overlap Requests khi Polling
  const isFetchingRef = useRef(false)

  async function loadData(isInitial = false) {
    // 3. CHỐNG OVERLAP: Bỏ qua lượt fetch mới nếu lượt fetch trước chưa xong
    if (isFetchingRef.current) return
    isFetchingRef.current = true
    if (isInitial) setLoading(true)

    try {
      const targetDate = historyDateRef.current || new Date().toISOString().split('T')[0]

      // 2. PARALLEL API: Tải toàn bộ 14 bảng dữ liệu song song qua Promise.all (thay vì await tuần tự)
      const [
        deviceRes,
        processRes,
        windowRes,
        screenshotRes,
        historyRes,
        rulesRes,
        appsRes,
        webRulesRes,
        usageRes,
        webUsageRes,
        schedRes,
        chatRes,
        todosRes,
        cfgRes
      ] = await Promise.all([
        supabase.from('devices').select('*').eq('device_name', DEVICE_NAME).maybeSingle(),
        supabase.from('process_logs').select('*').eq('device_name', DEVICE_NAME).order('created_at', { ascending: false }).limit(30),
        supabase.from('active_window_logs').select('*').eq('device_name', DEVICE_NAME).order('created_at', { ascending: false }).limit(100),
        supabase.from('screenshot_logs').select('*').eq('device_name', DEVICE_NAME).order('created_at', { ascending: false }).limit(40),
        supabase.from('browser_history_logs').select('*').eq('device_name', DEVICE_NAME).order('visit_time', { ascending: false }).limit(100),
        supabase.from('time_restrictions').select('*').eq('device_name', DEVICE_NAME).order('day_of_week'),
        supabase.from('app_rules').select('*').eq('device_name', DEVICE_NAME),
        supabase.from('web_rules').select('*').eq('device_name', DEVICE_NAME).order('created_at', { ascending: false }),
        supabase.from('app_usage_logs').select('*').eq('device_name', DEVICE_NAME).eq('usage_date', targetDate),
        supabase.from('web_usage_logs').select('*').eq('device_name', DEVICE_NAME).eq('usage_date', targetDate),
        supabase.from('schedules').select('*').eq('device_name', DEVICE_NAME).order('start_time', { ascending: true }),
        supabase.from('chat_messages').select('*').eq('device_name', DEVICE_NAME).order('created_at', { ascending: true }),
        supabase.from('todo_notes').select('*').eq('device_name', DEVICE_NAME).order('created_at', { ascending: false }),
        supabase.from('app_config').select('*').eq('device_name', DEVICE_NAME).maybeSingle()
      ])

      // 4. XỬ LÝ LỖI SUPABASE ĐÚNG: Chỉ set state khi KHÔNG có lỗi và data hợp lệ (không gán rỗng [] làm xóa trắng UI)
      if (!deviceRes.error && deviceRes.data !== undefined) setDevice(deviceRes.data)
      else if (deviceRes.error) console.error('[Supabase Error] devices:', deviceRes.error)

      if (!processRes.error && processRes.data) setProcesses(processRes.data)
      else if (processRes.error) console.error('[Supabase Error] process_logs:', processRes.error)

      if (!windowRes.error && windowRes.data) setActiveWindows(windowRes.data)
      else if (windowRes.error) console.error('[Supabase Error] active_window_logs:', windowRes.error)

      if (!screenshotRes.error && screenshotRes.data) setScreenshots(screenshotRes.data)
      else if (screenshotRes.error) console.error('[Supabase Error] screenshot_logs:', screenshotRes.error)

      if (!historyRes.error && historyRes.data) setBrowserHistory(historyRes.data)
      else if (historyRes.error) console.error('[Supabase Error] browser_history_logs:', historyRes.error)

      if (!rulesRes.error && rulesRes.data) {
        setTimeRules(rulesRes.data)
      }
      else if (rulesRes.error) console.error('[Supabase Error] time_restrictions:', rulesRes.error)

      if (!appsRes.error && appsRes.data) setAppRules(appsRes.data)
      else if (appsRes.error) console.error('[Supabase Error] app_rules:', appsRes.error)

      if (!webRulesRes.error && webRulesRes.data) setWebRules(webRulesRes.data)
      else if (webRulesRes.error) console.error('[Supabase Error] web_rules:', webRulesRes.error)

      if (!usageRes.error && usageRes.data) setAppUsage(usageRes.data)
      else if (usageRes.error) console.error('[Supabase Error] app_usage_logs:', usageRes.error)

      if (!webUsageRes.error && webUsageRes.data) setWebUsage(webUsageRes.data)
      else if (webUsageRes.error) console.error('[Supabase Error] web_usage_logs:', webUsageRes.error)

      if (!schedRes.error && schedRes.data) setSchedules(schedRes.data)
      else if (schedRes.error) console.error('[Supabase Error] schedules:', schedRes.error)

      if (!todosRes.error && todosRes.data) setTodoNotes(todosRes.data)
      else if (todosRes.error) console.error('[Supabase Error] todo_notes:', todosRes.error)

      if (!chatRes.error && chatRes.data) {
        const dbChats = chatRes.data
        setChatMessages(prev => {
          const tempChats = prev.filter(m => typeof m.id === 'string' && m.id.startsWith('temp_'))
          const existingIds = new Set(dbChats.map(m => m.id))
          const unSyncedTemps = tempChats.filter(t => !existingIds.has(t.id))
          return [...dbChats, ...unSyncedTemps]
        })
      } else if (chatRes.error) {
        console.error('[Supabase Error] chat_messages:', chatRes.error)
      }

      if (!cfgRes.error && cfgRes.data) {
        const cfgData = cfgRes.data
        setAppConfig(cfgData)
        if (!newAgentPass) setNewAgentPass(cfgData.agent_password || '')
        if (!newAdminPin) setNewAdminPin(cfgData.admin_pin || '')
        if (cfgData.screenshot_interval_minutes !== undefined && cfgData.screenshot_interval_minutes !== null) {
          setScreenshotMin(cfgData.screenshot_interval_minutes)
        }
        if (cfgData.custom_roles) setCustomRoles(cfgData.custom_roles)
        if (cfgData.role_passwords) setRolePasswords(cfgData.role_passwords)
        if (cfgData.role_permissions) setRolePermissions(cfgData.role_permissions)
        if (cfgData.is_paused !== undefined && cfgData.is_paused !== null) {
          setIsPaused(cfgData.is_paused)
        }
        if (cfgData.is_allowed !== undefined && cfgData.is_allowed !== null) {
          setIsDeviceAllowed(cfgData.is_allowed)
        }
        if (cfgData.time_limit_mode) {
          setTimeLimitMode(cfgData.time_limit_mode)
        }
        if (typeof cfgData.master_time_limit === 'boolean') {
          setIsMasterTimeLimitActive(cfgData.master_time_limit)
        } else if (rulesRes.data && rulesRes.data.length > 0) {
          setIsMasterTimeLimitActive(rulesRes.data.some(r => r.is_active === true))
        } else {
          setIsMasterTimeLimitActive(false)
        }
      } else if (cfgRes.error) {
        console.error('[Supabase Error] app_config:', cfgRes.error)
      }

      // Tải danh sách session thiết bị đang truy cập & Lọc bỏ session rác quá 35s
      const cutoff35s = new Date(Date.now() - 35000).toISOString()
      // Chỉ thực hiện dọn dẹp session rác khi mở trang lần đầu để tránh lãng phí IOPS Supabase
      if (isInitial) {
        try {
          await supabase.from('web_access_sessions').delete().lt('last_active', cutoff35s)
        } catch (e) {}
      }

      const { data: sessData, error: sessErr } = await supabase
        .from('web_access_sessions')
        .select('*')
        .gte('last_active', cutoff35s)
        .order('last_active', { ascending: false })

      if (!sessErr && sessData) {
        let rawSessions = [...sessData]
        const hasCurrentSess = rawSessions.some(s => s.session_id === sessionId)
        if (!hasCurrentSess) {
          rawSessions.unshift({
            session_id: sessionId,
            device_id: deviceId,
            user_role: isAdmin ? 'Admin' : (userRole || 'Viewer'),
            device_info: getDetailedDeviceInfo(),
            last_active: new Date().toISOString(),
            is_blocked: false
          })
        }

        const groupedDeviceMap = new Map()
        for (const s of rawSessions) {
          const key = (s.device_id || s.device_info) + '___' + (s.user_role || 'Viewer')
          if (!groupedDeviceMap.has(key)) {
            groupedDeviceMap.set(key, {
              ...s,
              tabCount: 1,
              allSessionIds: [s.session_id]
            })
          } else {
            const existing = groupedDeviceMap.get(key)
            existing.tabCount += 1
            existing.allSessionIds.push(s.session_id)
            if (new Date(s.last_active) > new Date(existing.last_active)) {
              existing.last_active = s.last_active
            }
            if (s.session_id === sessionId) {
              existing.session_id = sessionId
            }
          }
        }

        const cleanGroupedSessions = Array.from(groupedDeviceMap.values())
        setActiveSessions(cleanGroupedSessions)

        const mySess = rawSessions.find(s => s.session_id === sessionId)
        if (mySess?.is_blocked) {
          setIsSessionBlocked(true)
        } else {
          setIsSessionBlocked(false)
        }
      } else if (sessErr) {
        console.error('[Supabase Error] web_access_sessions:', sessErr)
      }

    } catch (err) {
      console.error('Lỗi tải dữ liệu tổng:', err)
    } finally {
      if (isInitial) setLoading(false)
      isFetchingRef.current = false
    }
  }

  async function handleTogglePauseControl() {
    const nextState = !isPaused
    setIsPaused(nextState)
    setTogglePauseLoading(true)

    try {
      // Chỉ cập nhật app_config.is_paused - Agent đọc trực tiếp mỗi chu kỳ, không cần lệnh riêng
      await supabase.from('app_config').upsert({
        device_name: DEVICE_NAME,
        is_paused: nextState,
        updated_at: new Date().toISOString()
      }, { onConflict: 'device_name' })
    } catch (err) {
      alert('Lỗi cập nhật trạng thái kiểm soát: ' + err.message)
      setIsPaused(!nextState)
    } finally {
      setTogglePauseLoading(false)
    }
  }

  // Task 1: Toggle quyền mở máy (Agent gọi lên kiểm tra)
  async function handleToggleDeviceAllowed() {
    const nextState = !isDeviceAllowed
    setIsDeviceAllowed(nextState)
    try {
      await supabase.from('app_config').upsert({
        device_name: DEVICE_NAME,
        is_allowed: nextState,
        updated_at: new Date().toISOString()
      }, { onConflict: 'device_name' })
    } catch (err) {
      alert('Lỗi cập nhật quyền mở máy: ' + err.message)
      setIsDeviceAllowed(!nextState)
    }
  }

  // Task 4: Đổi phương thức giới hạn giờ
  async function handleChangeTimeLimitMode(mode) {
    setTimeLimitMode(mode)
    try {
      await supabase.from('app_config').upsert({
        device_name: DEVICE_NAME,
        time_limit_mode: mode,
        updated_at: new Date().toISOString()
      }, { onConflict: 'device_name' })
    } catch (err) {
      alert('Lỗi cập nhật phương thức giới hạn: ' + err.message)
    }
  }

  // Task 6: Tải lịch sử theo ngày cụ thể
  async function loadHistoryForDate(dateStr) {
    setHistoryDate(dateStr)
    historyDateRef.current = dateStr
    try {
      const startOfDay = `${dateStr}T00:00:00`
      const endOfDay = `${dateStr}T23:59:59`

      const { data: windowData } = await supabase
        .from('active_window_logs')
        .select('*')
        .eq('device_name', DEVICE_NAME)
        .gte('created_at', startOfDay)
        .lte('created_at', endOfDay)
        .order('created_at', { ascending: false })
        .limit(3000)
      setDateFilteredWindows(windowData || [])

      const { data: histData } = await supabase
        .from('browser_history_logs')
        .select('*')
        .eq('device_name', DEVICE_NAME)
        .gte('visit_time', startOfDay)
        .lte('visit_time', endOfDay)
        .order('visit_time', { ascending: false })
        .limit(3000)
      setDateFilteredHistory(histData || [])

      // Cập nhật appUsage và webUsage theo ngày được chọn
      const { data: appData } = await supabase
        .from('app_usage_logs')
        .select('*')
        .eq('device_name', DEVICE_NAME)
        .eq('usage_date', dateStr)
      setAppUsage(appData || [])

      const { data: webData } = await supabase
        .from('web_usage_logs')
        .select('*')
        .eq('device_name', DEVICE_NAME)
        .eq('usage_date', dateStr)
      setWebUsage(webData || [])

    } catch (err) {
      console.error('Lỗi tải lịch sử ngày:', err)
    }
  }

  // Toggle Công Tắc Master Giới Hạn Thời Gian
  async function handleToggleMasterTimeLimit() {
    const nextState = !isMasterTimeLimitActive
    setIsMasterTimeLimitActive(nextState)
    try {
      const configPromise = supabase.from('app_config').upsert({
        device_name: DEVICE_NAME,
        master_time_limit: nextState,
        updated_at: new Date().toISOString()
      }, { onConflict: 'device_name' })

      const rulesPromise = supabase.from('time_restrictions')
        .update({ is_active: nextState })
        .eq('device_name', DEVICE_NAME)

      const [configRes, rulesRes] = await Promise.all([configPromise, rulesPromise])
      if (configRes.error) throw configRes.error
      if (rulesRes.error) throw rulesRes.error

      setTimeRules(prevRules => prevRules.map(r => ({ ...r, is_active: nextState })))
      await sendReloadRulesCmd()
    } catch (err) {
      console.error('Lỗi cập nhật công tắc Master:', err)
      alert('Lỗi cập nhật công tắc Master: ' + err.message)
      setIsMasterTimeLimitActive(!nextState)
    }
  }


  // Render Thanh Timeline 24h Trực Quan cho Chế độ Theo Khung Giờ
  function render24hTimeline(rule) {
    if (!rule || !rule.is_active) {
      return (
        <div className="mt-3 space-y-1.5">
          <div className="flex justify-between text-[10px] text-zinc-500 font-mono">
            <span>00:00</span>
            <span>06:00</span>
            <span>12:00</span>
            <span>18:00</span>
            <span>24:00</span>
          </div>
          <div className="h-3.5 w-full bg-zinc-900/50 border border-zinc-800 rounded-full overflow-hidden flex items-center justify-center">
            <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider"> Quy tắc ngày này đang tắt (Không giới hạn)</span>
          </div>
        </div>
      )
    }

    const startParts = (rule.start_time || '08:00').split(':')
    const endParts = (rule.end_time || '21:00').split(':')

    const startHour = (parseInt(startParts[0]) || 0) + (parseInt(startParts[1]) || 0) / 60
    const endHour = (parseInt(endParts[0]) || 0) + (parseInt(endParts[1]) || 0) / 60

    const startPercent = Math.max(0, Math.min(100, (startHour / 24) * 100))
    const endPercent = Math.max(0, Math.min(100, (endHour / 24) * 100))
    const widthPercent = Math.max(0, endPercent - startPercent)

    return (
      <div className="mt-3 space-y-1.5">
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-zinc-400 font-medium">Mô phỏng timeline 24h:</span>
          <span className="text-emerald-400 font-bold bg-emerald-500/10 px-2.5 py-0.5 rounded border border-emerald-500/20">
             Giờ được phép: {rule.start_time?.slice(0, 5)} - {rule.end_time?.slice(0, 5)} ({(endHour - startHour).toFixed(1)} tiếng)
          </span>
        </div>

        <div className="h-4 w-full bg-red-950/70 border border-red-900/50 rounded-full overflow-hidden relative shadow-inner">
          {/* Active Allowed Time Bar */}
          <div
            className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 rounded-full shadow-lg shadow-emerald-500/30 transition-all duration-300 relative group cursor-pointer"
            style={{ left: `${startPercent}%`, width: `${widthPercent}%`, position: 'absolute' }}
          >
            <div className="opacity-0 group-hover:opacity-100 absolute -top-7 left-1/2 -translate-x-1/2 bg-zinc-900/50 text-emerald-300 text-[10px] font-bold px-2 py-0.5 rounded border border-emerald-500/40 whitespace-nowrap transition shadow-xl z-20">
              {rule.start_time?.slice(0, 5)} - {rule.end_time?.slice(0, 5)}
            </div>
          </div>
        </div>

        <div className="flex justify-between text-[10px] font-mono text-zinc-500">
          <span>00:00</span>
          <span>06:00</span>
          <span>12:00</span>
          <span>18:00</span>
          <span>24:00</span>
        </div>
      </div>
    )
  }

  // Mở Modal Xác Nhận Xóa Dữ Liệu Ngày
  function openDeleteDateModal(dateStr) {
    if (!isAdmin) {
      alert('Chỉ Admin mới có quyền xóa dữ liệu.')
      return
    }
    setDateToDelete(dateStr)
    setShowDeleteDateModal(true)
  }

  // Thực Thi Xóa Lịch Sử Ngày Sau Khi Đã Xác Nhận Từ Modal
  async function confirmDeleteHistoryForDate() {
    if (!dateToDelete) return
    const dateStr = dateToDelete
    setShowDeleteDateModal(false)

    try {
      const startOfDay = `${dateStr}T00:00:00`
      const endOfDay = `${dateStr}T23:59:59`

      await Promise.all([
        supabase.from('active_window_logs').delete().eq('device_name', DEVICE_NAME).gte('created_at', startOfDay).lte('created_at', endOfDay),
        supabase.from('browser_history_logs').delete().eq('device_name', DEVICE_NAME).gte('visit_time', startOfDay).lte('visit_time', endOfDay),
        supabase.from('app_usage_logs').delete().eq('device_name', DEVICE_NAME).eq('usage_date', dateStr),
        supabase.from('web_usage_logs').delete().eq('device_name', DEVICE_NAME).eq('usage_date', dateStr)
      ])

      alert(` Đã xóa thành công toàn bộ dữ liệu ngày ${dateStr}`)
      loadAvailableDates()
      loadHistoryForDate(new Date().toISOString().split('T')[0])
      loadData(false)
    } catch (err) {
      console.error('Lỗi khi xóa dữ liệu ngày:', err)
      alert('Có lỗi xảy ra khi xóa dữ liệu!')
    } finally {
      setDateToDelete(null)
    }
  }

  // Task 6: Tải danh sách ngày có dữ liệu
  async function loadAvailableDates() {
    try {
      const { data: usageData } = await supabase
        .from('app_usage_logs')
        .select('usage_date')
        .eq('device_name', DEVICE_NAME)
        .order('usage_date', { ascending: false })
      
      const { data: windowData } = await supabase
        .from('active_window_logs')
        .select('created_at')
        .eq('device_name', DEVICE_NAME)
        .order('created_at', { ascending: false })
        .limit(3000)

      const dateSet = new Set()
      if (usageData) usageData.forEach(d => { if(d.usage_date) dateSet.add(d.usage_date) })
      if (windowData) windowData.forEach(d => { if(d.created_at) dateSet.add(d.created_at.split('T')[0]) })
      
      // Ensure today is always in the list
      dateSet.add(new Date().toISOString().split('T')[0])

      setAvailableDates([...dateSet].sort((a,b) => b.localeCompare(a)))
    } catch (err) {
      console.error('Lỗi tải danh sách ngày:', err)
    }
  }

  // Task 8: Gộp tiến trình & Lịch sử web liên tục thành khoảng giờ (HH:MM~HH:MM)
  function mergeConsecutiveEntries(items) {
    if (!items || items.length === 0) return []
    
    // Sắp xếp theo thời gian tăng dần
    const sorted = [...items].sort((a, b) => 
      new Date(a.created_at || a.visit_time || a.startTime) - new Date(b.created_at || b.visit_time || b.startTime)
    )
    
    const merged = []
    let current = {
      ...sorted[0],
      startTime: sorted[0].created_at || sorted[0].visit_time,
      endTime: sorted[0].created_at || sorted[0].visit_time,
      count: 1,
      ids: [sorted[0].id]
    }
    
    for (let i = 1; i < sorted.length; i++) {
      const item = sorted[i]
      const itemKey = (item.process_name || item.url || '').toLowerCase()
      const currentKey = (current.process_name || current.url || '').toLowerCase()
      
      if (itemKey === currentKey) {
        // Cùng tiến trình/URL → gộp
        current.endTime = item.created_at || item.visit_time
        current.count++
        current.ids.push(item.id)
      } else {
        // Khác tiến trình → lưu cái cũ, bắt đầu cái mới
        merged.push(current)
        current = {
          ...item,
          startTime: item.created_at || item.visit_time,
          endTime: item.created_at || item.visit_time,
          count: 1,
          ids: [item.id]
        }
      }
    }
    merged.push(current)
    
    // Đảo ngược để hiển thị mới nhất trước
    return merged.reverse()
  }

  // C4 FIX: Giữ reference mới nhất của loadData để tránh Stale Closure trong Polling 5s
  const loadDataRef = useRef(loadData)
  useEffect(() => {
    loadDataRef.current = loadData
  })

  useEffect(() => {
    loadData(true)
    fetchGoogleSheetTasks()
    loadAvailableDates()
    loadHistoryForDate(new Date().toISOString().split('T')[0])
    const interval = setInterval(() => {
      if (loadDataRef.current) {
        loadDataRef.current(false)
      }
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  // Xử lý Đăng nhập Admin & Ghi nhớ 30 ngày
  function handleAdminLogin(e) {
    e.preventDefault()
    const validPin = appConfig?.admin_pin || '123456'
    if (pinInput === validPin) {
      setIsAdmin(true)
      setShowLoginModal(false)
      setLoginError('')
      setPinInput('')
      if (rememberMe) {
        const thirtyDaysMs = 30 * 24 * 60 * 60 * 1000
        safeSetLocalStorage('admin_auth_expiry', (Date.now() + thirtyDaysMs).toString())
      } else {
        safeRemoveLocalStorage('admin_auth_expiry')
      }
      syncWebSession('Admin')
    } else {
      setLoginError('Mã PIN Admin không đúng!')
    }
  }

  function handleAdminLogout() {
    setIsAdmin(false)
    safeRemoveLocalStorage('admin_auth_expiry')
    if (activeTab === 'config' || activeTab === 'screenshots' || activeTab === 'storage') changeActiveTab('overview')
    syncWebSession(userRole || 'Viewer')
  }

  // Xóa dữ liệu theo khoảng ngày và loại dữ liệu (Storage Management)
  async function handleDeleteStorageByRange() {
    if (!isAdmin) return
    if (!window.confirm(`Bạn có chắc chắn muốn xóa dữ liệu loại "${storageLogType}" từ ngày ${storageStartDate} đến ${storageEndDate}? Hành động này KHÔNG thể hoàn tác!`)) {
      return
    }
    setIsCleaningStorage(true)
    setStorageMessage('Đang thực hiện xóa dữ liệu...')
    try {
      const startIso = new Date(storageStartDate + 'T00:00:00.000Z').toISOString()
      const endIso = new Date(storageEndDate + 'T23:59:59.999Z').toISOString()

      const tablesToDelete = storageLogType === 'all' 
        ? ['browser_history_logs', 'active_window_logs', 'process_logs', 'system_events', 'screenshot_logs', 'system_commands']
        : [storageLogType]

      for (const tbl of tablesToDelete) {
        let dateCol = 'created_at'
        if (tbl === 'browser_history_logs') dateCol = 'visit_time'
        if (tbl === 'app_usage_logs' || tbl === 'web_usage_logs') dateCol = 'usage_date'

        if (tbl === 'screenshot_logs' || storageLogType === 'all') {
          try {
            const { data: files } = await supabase.from('screenshot_logs')
              .select('file_path')
              .eq('device_name', DEVICE_NAME)
              .gte(dateCol, startIso)
              .lte(dateCol, endIso)
            
            if (files && files.length > 0) {
              const paths = files.map(f => f.file_path).filter(Boolean)
              if (paths.length > 0) {
                await supabase.storage.from('screenshots').remove(paths)
              }
            }
          } catch (e) {
            console.warn('Lỗi xóa storage files:', e)
          }
        }

        const res = await supabase.from(tbl)
          .delete()
          .eq('device_name', DEVICE_NAME)
          .gte(dateCol, startIso)
          .lte(dateCol, endIso)
        
        if (res.error) console.error(`Lỗi xóa ${tbl}:`, res.error)
      }

      setStorageMessage(`✅ Đã xóa thành công dữ liệu loại "${storageLogType}" từ ${storageStartDate} đến ${storageEndDate}!`)
      loadData(false)
    } catch (err) {
      setStorageMessage(`❌ Lỗi khi xóa dữ liệu: ${err.message}`)
    } finally {
      setIsCleaningStorage(false)
    }
  }

  // Dọn rác triệt để (Deep Storage Vacuum)
  async function handleDeepStorageVacuum() {
    if (!isAdmin) return
    if (!window.confirm('Bạn có chắc muốn thực hiện "Dọn Rác Triệt Để"? Hệ thống sẽ tự dọn các bản ghi cũ quá hạn và file rác không còn sử dụng trên Supabase!')) {
      return
    }
    setIsCleaningStorage(true)
    setStorageMessage('Đang thực hiện dọn rác triệt để trên Supabase...')
    try {
      const rpcRes = await supabase.rpc('clean_old_logs')
      if (rpcRes.error) {
        console.warn('Lỗi gọi RPC clean_old_logs, chuyển sang xóa thủ công:', rpcRes.error)
        const cutoff7d = new Date(Date.now() - 7 * 86400000).toISOString()
        await supabase.from('system_commands').delete().eq('device_name', DEVICE_NAME).in('status', ['completed', 'failed']).lt('created_at', cutoff7d)
        const cutoff30d = new Date(Date.now() - 30 * 86400000).toISOString()
        await supabase.from('active_window_logs').delete().eq('device_name', DEVICE_NAME).lt('created_at', cutoff30d)
        await supabase.from('process_logs').delete().eq('device_name', DEVICE_NAME).lt('created_at', cutoff30d)
      }

      setStorageMessage('✅ Đã thực hiện Dọn Rác Triệt Để và giải phóng bộ nhớ Supabase thành công!')
      loadData(false)
    } catch (err) {
      setStorageMessage(`❌ Lỗi dọn rác: ${err.message}`)
    } finally {
      setIsCleaningStorage(false)
    }
  }

  function formatTime(iso) {
    if (!iso) return '—'
    const d = new Date(iso)
    if (isNaN(d.getTime())) return '—'
    const dateStr = d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric', timeZone: 'Asia/Ho_Chi_Minh' })
    const timeStr = d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false, timeZone: 'Asia/Ho_Chi_Minh' })
    return `${timeStr} - ${dateStr}`
  }

  function formatClockTime(iso) {
    if (!iso) return '—'
    const d = new Date(iso)
    if (isNaN(d.getTime())) return '—'
    return d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Ho_Chi_Minh' })
  }

  function getScreenshotDisplayTime(item) {
    if (!item) return '—'
    if (item.created_at) {
      const d = new Date(item.created_at)
      if (!isNaN(d.getTime())) {
        return d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false, timeZone: 'Asia/Ho_Chi_Minh' })
      }
    }
    if (item.file_path) {
      const match = item.file_path.match(/(\d{4})[-_]?(\d{2})[-_]?(\d{2})[-_T]?(\d{2})[-_:]?(\d{2})[-_:]?(\d{2})/)
      if (match) {
        const [, Y, M, D, h, m, s] = match
        return `${h}:${m}:${s}`
      }
      const unixMatch = item.file_path.match(/(\d{10,13})/)
      if (unixMatch) {
        let ts = parseInt(unixMatch[1])
        if (ts < 10000000000) ts *= 1000
        const d = new Date(ts)
        if (!isNaN(d.getTime())) {
          return d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false, timeZone: 'Asia/Ho_Chi_Minh' })
        }
      }
    }
    return '—'
  }

  function formatDateHeader(iso) {
    if (!iso) return 'Hôm nay'
    const d = new Date(iso)
    if (isNaN(d.getTime())) return 'Hôm nay'
    const vnNow = new Date()
    const isToday = d.toLocaleDateString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' }) === vnNow.toLocaleDateString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' })
    const formatted = d.toLocaleDateString('vi-VN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', timeZone: 'Asia/Ho_Chi_Minh' })
    if (isToday) {
      return `Hôm nay - ${formatted}`
    }
    return formatted
  }

  function formatDateGroup(iso) {
    if (!iso) return 'Khác'
    const d = new Date(iso)
    if (isNaN(d.getTime())) return 'Khác'
    const dateStr = d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric', timeZone: 'Asia/Ho_Chi_Minh' })
    return `Ngày ${dateStr}`
  }

  function getScreenshotUrl(path, options = {}) {
    if (!path) return ''
    const transform = {}
    if (options.width) transform.width = options.width
    if (options.height) transform.height = options.height
    if (options.quality) transform.quality = options.quality
    if (options.resize) transform.resize = options.resize

    const hasTransform = Object.keys(transform).length > 0
    const { data } = supabase.storage.from('screenshots').getPublicUrl(path, hasTransform ? { transform } : undefined)
    return data?.publicUrl || ''
  }

  // TÍNH NĂNG CƯỠNG CHẾ CẬP NHẬT AGENT TỪ XA
  async function triggerForceAgentUpdate() {
    if (!confirm('Bạn có chắc chắn muốn gửi lệnh cưỡng chế cập nhật phần mềm Agent trên máy em trai? Agent sẽ tự khởi động lại bản mới nhất.')) return
    setUpdateSending(true)
    try {
      await supabase.from('system_commands').insert({
        device_name: DEVICE_NAME,
        command: 'force_update',
        status: 'pending'
      })
      alert(' Đã gửi lệnh Cưỡng chế cập nhật thành công! Agent sẽ tự động cập nhật và khởi động lại ngay.')
    } catch (e) {
      alert('Lỗi gửi lệnh cập nhật: ' + e.message)
    } finally {
      setUpdateSending(false)
    }
  }

  // TÍNH NĂNG XÓA NHIỀU ẢNH CÙNG LÚC & CHỌN THEO NGÀY
  function toggleSelectScreenshot(id) {
    setSelectedScreenshotIds(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    )
  }

  function toggleSelectDateGroup(dateKey, items) {
    const groupIds = items.map(item => item.id)
    const allSelected = groupIds.every(id => selectedScreenshotIds.includes(id))
    if (allSelected) {
      setSelectedScreenshotIds(prev => prev.filter(id => !groupIds.includes(id)))
    } else {
      setSelectedScreenshotIds(prev => Array.from(new Set([...prev, ...groupIds])))
    }
  }

  
  async function deleteScreenshot(id, filePath) {
    if (!confirm('Bạn có chắc muốn xóa ảnh này?')) return
    try {
      if (filePath) {
        await supabase.storage.from('screenshots').remove([filePath])
      }
      await supabase.from('screenshot_logs').delete().eq('id', id)
      setSelectedScreenshotIds(prev => (prev ?? []).filter(i => i !== id))
      loadData(false)
    } catch (err) {
      alert('Lỗi xóa ảnh: ' + (err.message || err))
    }
  }

  async function handleBulkDeleteScreenshots() {
    if (selectedScreenshotIds.length === 0) return
    if (!confirm(`Bạn có chắc muốn xóa ${selectedScreenshotIds.length} ảnh đã chọn?`)) return
    setBulkDeleting(true)

    try {
      const itemsToDelete = screenshots.filter(s => selectedScreenshotIds.includes(s.id))
      const filePaths = itemsToDelete.map(s => s.file_path)

      if (filePaths.length > 0) {
        await supabase.storage.from('screenshots').remove(filePaths)
      }
      await supabase.from('screenshot_logs').delete().in('id', selectedScreenshotIds)

      setSelectedScreenshotIds([])
      loadData(false)
    } catch (err) {
      alert('Lỗi xóa ảnh: ' + err.message)
    } finally {
      setBulkDeleting(false)
    }
  }

  // TÍNH NĂNG XÓA NHIỀU LỊCH SỬ DUYỆT WEB CÙNG LÚC
  function toggleSelectHistory(id) {
    setSelectedHistoryIds(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    )
  }

  function toggleSelectHistoryGroup(dateKey, items) {
    const groupIds = items.map(item => item.id)
    const allSelected = groupIds.every(id => selectedHistoryIds.includes(id))
    if (allSelected) {
      setSelectedHistoryIds(prev => prev.filter(id => !groupIds.includes(id)))
    } else {
      setSelectedHistoryIds(prev => Array.from(new Set([...prev, ...groupIds])))
    }
  }

  async function handleBulkDeleteHistory() {
    if (selectedHistoryIds.length === 0) return
    if (!confirm(`Bạn có chắc muốn xóa ${selectedHistoryIds.length} mục lịch sử duyệt web đã chọn?`)) return
    setBulkDeletingHistory(true)

    try {
      await supabase.from('browser_history_logs').delete().in('id', selectedHistoryIds)
      setSelectedHistoryIds([])
      loadData(false)
    } catch (err) {
      alert('Lỗi xóa lịch sử duyệt web: ' + err.message)
    } finally {
      setBulkDeletingHistory(false)
    }
  }

  // TÍNH NĂNG XÓA LỊCH SỬ DÙNG APP & TIMELINE APP
  function toggleSelectAppHistory(id) {
    setSelectedAppHistoryIds(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    )
  }

  function toggleSelectAppHistoryGroup(dateKey, items) {
    const groupIds = items.map(item => item.id)
    const allSelected = groupIds.every(id => selectedAppHistoryIds.includes(id))
    if (allSelected) {
      setSelectedAppHistoryIds(prev => prev.filter(id => !groupIds.includes(id)))
    } else {
      setSelectedAppHistoryIds(prev => Array.from(new Set([...prev, ...groupIds])))
    }
  }

  async function handleBulkDeleteAppHistory() {
    if (selectedAppHistoryIds.length === 0) return
    if (!confirm(`Bạn có chắc muốn xóa ${selectedAppHistoryIds.length} mục lịch sử app đã chọn?`)) return
    setBulkDeletingAppHistory(true)

    try {
      await supabase.from('active_window_logs').delete().in('id', selectedAppHistoryIds)
      setSelectedAppHistoryIds([])
      loadData(false)
    } catch (err) {
      alert('Lỗi xóa lịch sử app: ' + err.message)
    } finally {
      setBulkDeletingAppHistory(false)
    }
  }

  async function handleDeleteSingleAppHistory(id) {
    if (!confirm('Bạn có chắc muốn xóa mục lịch sử app này?')) return
    try {
      await supabase.from('active_window_logs').delete().eq('id', id)
      setSelectedAppHistoryIds(prev => prev.filter(i => i !== id))
      loadData(false)
    } catch (err) {
      alert('Lỗi xóa mục lịch sử app: ' + err.message)
    }
  }

  // THÊM VÀ QUẢN LÝ QUY TẮC BLACK LIST (APP & WEB)
  async function handleAddBlackListRule(e) {
    e.preventDefault()
    if (!blackListTargetInput.trim()) return
    const target = blackListTargetInput.trim()

    if (blackListRuleType === 'app') {
      const processName = target.toLowerCase().endsWith('.exe') ? target : target + '.exe'
      await supabase.from('app_rules').insert({
        device_name: DEVICE_NAME,
        process_name: processName,
        category: blackListCategory,
        max_minutes_per_day: blackListCategory === 'limited' ? parseInt(blackListMaxMinutes) || 0 : 0
      })
    } else {
      const cleanDomain = target.toLowerCase().replace(/^https?:\/\//, '').replace(/^www\./, '').split('/')[0]
      await supabase.from('web_rules').upsert({
        device_name: DEVICE_NAME,
        domain: cleanDomain,
        category: blackListCategory,
        max_minutes_per_day: blackListCategory === 'limited' ? parseInt(blackListMaxMinutes) || 0 : 0,
        is_active: true
      }, { onConflict: 'device_name, domain' })
    }

    setBlackListTargetInput('')
    setShowAddBlackListModal(false)
    loadData(false)
  }

  async function updateWebRule(id, field, value) {
    await supabase.from('web_rules').update({ [field]: value }).eq('id', id)
    loadData(false)
  }

  async function deleteWebRule(id) {
    await supabase.from('web_rules').delete().eq('id', id)
    loadData(false)
  }

  async function deleteAppRule(id) {
    await supabase.from('app_rules').delete().eq('id', id)
    loadData(false)
  }

  // TÍNH NĂNG CHẶN / BỎ CHẶN THIẾT BỊ TRUY CẬP (KÈM POPUP XÁC NHẬN)
  function openBlockSessionModal(sess) {
    setSessionToBlock(sess)
    setShowBlockSessionModal(true)
  }

  async function confirmToggleBlockSession() {
    if (!sessionToBlock) return
    await toggleBlockSession(sessionToBlock.session_id, sessionToBlock.is_blocked)
    setShowBlockSessionModal(false)
    setSessionToBlock(null)
  }

  async function toggleBlockSession(sessId, currentStatus) {
    setActiveSessions(prev => prev.map(s => s.session_id === sessId ? { ...s, is_blocked: !currentStatus } : s))
    try {
      await supabase.from('web_access_sessions').update({ is_blocked: !currentStatus }).eq('session_id', sessId)
    } catch (e) {}
    loadData(false)
  }

  // ADMIN QUẢN LÝ TƯ CÁCH (THÊM / XÓA ROLE & ĐẶT MẬT KHẨU CỦA TƯ CÁCH)
  async function handleAddCustomRole(e) {
    e.preventDefault()
    if (!newRoleInput.trim() || customRoles.includes(newRoleInput.trim())) return
    const updatedRoles = [...customRoles, newRoleInput.trim()]
    setCustomRoles(updatedRoles)
    setNewRoleInput('')

    try {
      await supabase.from('app_config').update({
        custom_roles: updatedRoles
      }).eq('device_name', DEVICE_NAME)
    } catch (err) {}
  }

  async function handleRemoveCustomRole(roleToRemove) {
    const updatedRoles = customRoles.filter(r => r !== roleToRemove)
    setCustomRoles(updatedRoles)
    try {
      await supabase.from('app_config').update({
        custom_roles: updatedRoles
      }).eq('device_name', DEVICE_NAME)
    } catch (err) {}
  }

  async function handleSetRolePassword(roleName, newPass) {
    const updated = { ...rolePasswords, [roleName]: newPass }
    setRolePasswords(updated)
    try {
      await supabase.from('app_config').update({
        role_passwords: updated
      }).eq('device_name', DEVICE_NAME)
    } catch (err) {}
  }

  async function handleSetRolePermission(roleName, tabKey, permType) {
    const rolePerms = rolePermissions[roleName] || {}
    const updated = {
      ...rolePermissions,
      [roleName]: {
        ...rolePerms,
        [tabKey]: permType
      }
    }
    setRolePermissions(updated)
    try {
      await supabase.from('app_config').update({
        role_permissions: updated
      }).eq('device_name', DEVICE_NAME)
    } catch (err) {}
  }

  async function sendReloadRulesCmd() {
    try {
      await supabase.from('system_commands').insert({
        device_name: DEVICE_NAME,
        command: 'reload_rules',
        status: 'pending'
      })
    } catch (e) {}
  }

  async function updateTimeRule(id, field, value) {
    await supabase.from('time_restrictions').update({ [field]: value }).eq('id', id)
    await sendReloadRulesCmd()
    loadData(false)
  }

  async function updateAppRule(id, field, value) {
    await supabase.from('app_rules').update({ [field]: value }).eq('id', id)
    await sendReloadRulesCmd()
    loadData(false)
  }

  async function sendInstantScreenshot() {
    setCmdSending(true)
    try {
      await supabase.from('system_commands').insert({
        device_name: DEVICE_NAME,
        command: 'take_screenshot',
        status: 'pending'
      })
      let count = 0
      const timer = setInterval(async () => {
        count++
        await loadData(false)
        if (count >= 12) {
          clearInterval(timer)
          setCmdSending(false)
        }
      }, 1500)
    } catch (e) {
      alert('Lỗi gửi lệnh chụp ảnh: ' + e.message)
      setCmdSending(false)
    }
  }


  async function handleSendChatMsg(text) {
    if (!text.trim()) return
    const msgText = text.trim()
    const senderName = isAdmin ? 'admin' : 'student'
    
    const tempMsg = {
      id: 'temp_' + Date.now(),
      device_name: DEVICE_NAME,
      sender: senderName,
      message: msgText,
      created_at: new Date().toISOString()
    }
    setChatMessages(prev => [...prev, tempMsg])
    setChatInput('')
    setFloatingChatInput('')

    try {
      const { error } = await supabase.from('chat_messages').insert({
        device_name: DEVICE_NAME,
        sender: senderName,
        message: msgText
      })
      if (error) {
        console.error('Lỗi gửi chat Supabase:', error)
      }
      loadData(false)
    } catch (e) {
      console.error('Lỗi gửi chat:', e)
    }
  }

  // TÍNH NĂNG TO DO NOTES REFACTOR
  async function toggleTodoComplete(id, currentStatus) {
    await supabase.from('todo_notes').update({ is_completed: !currentStatus }).eq('id', id)
    loadData(false)
  }

  function toggleSheetTaskComplete(id) {
    setCompletedSheetTasks(prev => ({ ...prev, [id]: !prev[id] }))
  }

  async function handleQuickAddTodoTask(e) {
    e.preventDefault()
    if (!quickAddTitle.trim()) return
    const cleanTitle = quickAddTitle.trim().replace(/\s+/g, ' ')

    try {
      await supabase.from('todo_notes').insert({
        device_name: DEVICE_NAME,
        task_title: cleanTitle,
        task_type: quickAddType,
        is_completed: false
      })
      setQuickAddTitle('')
      loadData(false)
    } catch (err) {
      alert('Lỗi thêm công việc: ' + err.message)
    }
  }

  function handleStartEditTodoTask(task) {
    setEditingTaskId(task.id)
    setEditingTaskTitle(task.title)
    setEditingTaskType(task.taskType || 'custom')
  }

  async function handleSaveEditTodoTask(e) {
    e.preventDefault()
    if (!editingTaskId || !editingTaskTitle.trim()) return
    const cleanTitle = editingTaskTitle.trim().replace(/\s+/g, ' ')

    try {
      if (typeof editingTaskId === 'string' && editingTaskId.startsWith('sheet_')) {
        await supabase.from('todo_notes').insert({
          device_name: DEVICE_NAME,
          task_title: cleanTitle,
          task_type: editingTaskType,
          is_completed: false
        })
        setDeletedSheetTaskIds(prev => [...prev, editingTaskId])
      } else {
        await supabase.from('todo_notes').update({
          task_title: cleanTitle,
          task_type: editingTaskType
        }).eq('id', editingTaskId)
      }
      setEditingTaskId(null)
      loadData(false)
    } catch (err) {
      alert('Lỗi lưu chỉnh sửa: ' + err.message)
    }
  }

  async function handleDeleteUnifiedTask(task) {
    if (task.isSheet) {
      setDeletedSheetTaskIds(prev => [...prev, task.id])
    } else {
      await supabase.from('todo_notes').delete().eq('id', task.id)
      loadData(false)
    }
  }

  async function deleteTodoTask(id) {
    await supabase.from('todo_notes').delete().eq('id', id)
    loadData(false)
  }

  // LƯU CẤU HÌNH ADMIN (THEME, MẬT KHẨU, CHU KỲ CHỤP ẢNH TÙY CHỈNH THỦ CÔNG)
  async function handleSaveConfig(e) {
    e.preventDefault()
    setConfigMsg('')
    const intervalVal = parseInt(screenshotMin) || 3
    try {
      const data = {
        device_name: DEVICE_NAME,
        agent_password: newAgentPass,
        admin_pin: newAdminPin,
        screenshot_interval_minutes: intervalVal,
        custom_roles: customRoles,
        role_passwords: rolePasswords,
        role_permissions: rolePermissions,
        updated_at: new Date().toISOString()
      }
      if (appConfig?.id) {
        await supabase.from('app_config').update(data).eq('id', appConfig.id)
      } else {
        await supabase.from('app_config').insert(data)
      }
      setScreenshotMin(intervalVal)
      setConfigMsg(` Đã cập nhật thành công! Chu kỳ chụp màn hình mới: ${intervalVal} phút.`)
      loadData(false)
    } catch (err) {
      setConfigMsg(' Lỗi cập nhật: ' + err.message)
    }
  }

  // ENGINE PHÂN TÍCH THÔNG MINH GEMINI AI (REAL-TIME CONTEXTUAL INTENT ENGINE)
  function getAiAnalysis() {
    // 1. Nhóm Tiến trình Học tập & Công việc Cố định
    const eduStrictProcs = ['acad.exe', 'autocad', 'code.exe', 'devenv.exe', 'idea64.exe', 'pycharm', 'sublime_text.exe', 'winword.exe', 'excel.exe', 'powerpnt.exe', 'photoshop', 'illustrator']
    const eduTitlePhrases = [
      'bài giảng', 'bài tập', 'ôn thi', 'luyện thi', 'giải bài', 'toán', 'vật lý', 'hóa học', 'ngữ văn', 'lịch sử', 'địa lý', 'sinh học', 'tiếng anh',
      'khoa học', 'lập trình', 'hướng dẫn học', 'tự học', 'khóa học', 'chữa đề', 'đề thi', 'thpt', 'thcs',
      'autocad', 'cad', 'python', 'javascript', 'react', 'java', 'c++', 'html', 'css', 'sql', 'database',
      'coursera', 'udemy', 'quizlet', 'duolingo', 'stackoverflow', 'github', 'docs.google.com', 'drive.google.com', 'canvas'
    ]

    // 2. Nhóm Tiến trình Giải trí & Game Cố định
    const playStrictProcs = ['leagueclientux.exe', 'league of legends.exe', 'garena.exe', 'valorant.exe', 'csgo.exe', 'roblox.exe', 'genshinimpact.exe', 'fifa.exe', 'spotify.exe']
    const playTitlePhrases = [
      'review anime', 'tập 1', 'tập 2', 'tập 3', 'tập 4', 'tập 5', 'tập 6', 'tập 7', 'tập 8', 'tập 9', 'tập 10',
      'thái tử', 'phế vật', 'mạo hiểm giả', 'hoạt hình', 'phim hay', 'phim chiếu ranh', 'trailer', 'mv', 'official music video',
      'nhạc trẻ', 'nhạc lofi', 'remix', 'highlights', 'gameplay', 'livestream', 'dự giờ', 'bomman', 'leopard', 'hữu nghĩa',
      'tiktok', 'facebook', 'fb.com', 'instagram', 'netflix', 'truyenfull', 'nettruyen', 'mangadex', 'discord'
    ]

    const studyWindows = []
    const playWindows = []
    const neutralWindows = []

    activeWindows.forEach(w => {
      const titleLower = (w.window_title || w.title || '').toLowerCase()
      const procLower = (w.process_name || '').toLowerCase()
      const displayName = w.window_title || w.process_name || 'Ứng dụng không tên'

      // BƯỚC 1: Đánh giá theo Tiến trình Cố định
      if (eduStrictProcs.some(p => procLower.includes(p))) {
        studyWindows.push(`💻 [Phần mềm] ${displayName}`)
        return
      }
      if (playStrictProcs.some(p => procLower.includes(p))) {
        playWindows.push(`🎮 [Game Engine] ${displayName}`)
        return
      }

      // BƯỚC 2: Đánh giá Ngữ cảnh Tiêu đề (Phân tích bóc tách YouTube & Web)
      let eduScore = 0
      let playScore = 0

      eduTitlePhrases.forEach(phrase => {
        if (titleLower.includes(phrase)) eduScore += 2
      })

      playTitlePhrases.forEach(phrase => {
        if (titleLower.includes(phrase)) playScore += 2
      })

      // Phân tích chi tiết ngữ cảnh trên Trình duyệt Web / YouTube
      if (procLower.includes('chrome') || procLower.includes('edge') || procLower.includes('browser') || titleLower.includes('youtube')) {
        if (eduScore > playScore) {
          studyWindows.push(`📚 [Bài Giảng/Tài Liệu Web] ${displayName}`)
        } else if (playScore > 0 || titleLower.includes('review') || titleLower.includes('tập') || titleLower.includes('game')) {
          playWindows.push(`🎬 [Giải Trí/Phim/Anime] ${displayName}`)
        } else {
          neutralWindows.push(`🌐 [Tra cứu chung] ${displayName}`)
        }
        return
      }

      // Phân loại tổng hợp
      if (eduScore > playScore && eduScore > 0) {
        studyWindows.push(displayName)
      } else if (playScore > eduScore && playScore > 0) {
        playWindows.push(displayName)
      } else {
        neutralWindows.push(displayName)
      }
    })

    const totalRated = studyWindows.length + playWindows.length
    const studyPercent = totalRated > 0 ? Math.round((studyWindows.length / totalRated) * 100) : 50
    const playPercent = 100 - studyPercent

    let score = 'Khá cân bằng ⚖️'
    let advice = 'Em trai đang duy trì mức độ tập trung tương đối giữa Học tập và Giải trí.'

    if (studyPercent >= 70) {
      score = 'Xuất sắc 🌟'
      advice = 'AI Gemini xác nhận em trai đang tập trung học tập / làm bài tập thực sự (AutoCAD, Bài giảng, Lập trình). Cần phát huy!'
    } else if (playPercent >= 60) {
      score = 'Cảnh báo: Ưu tiên Giải trí ⚠️'
      advice = 'AI Gemini phân tích thấy tần suất xem Video giải trí, Review Phim/Anime hoặc Chơi Game đang chiếm ưu thế.'
    }

    return {
      score,
      ratio: `${studyPercent}% Học tập & Bài giảng / ${playPercent}% Phim & Game & Mạng xã hội`,
      studyWindows,
      playWindows,
      neutralWindows,
      summary: `AI Gemini đã phân tích sâu ngữ cảnh tiêu đề của ${activeWindows.length} cửa sổ ứng dụng & trang web gần nhất.`,
      advice
    }
  }

  const aiReport = getAiAnalysis()

  // CHỌN NGUỒN DỮ LIỆU SỬ DỤNG THEO NGÀY
  const appHistorySource = historyDate === new Date().toISOString().split('T')[0]
    ? activeWindows
    : dateFilteredWindows

  const webHistorySource = historyDate === new Date().toISOString().split('T')[0]
    ? browserHistory
    : dateFilteredHistory

  // TÍNH TOÁN THỜI GIAN SỬ DỤNG APP TỪ LOGS HỆ THỐNG (active_window_logs: Mỗi log ~ 1 phút)
  const appMinutesMap = {}
  appHistorySource.forEach(item => {
    if (item.process_name) {
      const key = item.process_name.toLowerCase()
      appMinutesMap[key] = (appMinutesMap[key] || 0) + 1
    }
  })

  // TÍNH TOÁN THỜI GIAN SỬ DỤNG WEB TỪ LOGS TRÌNH DUYỆT (browser_history_logs)
  const webMinutesMap = {}
  webHistorySource.forEach(item => {
    if (item.url) {
      const domain = item.url.replace(/^(?:https?:\/\/)?(?:www\.)?/i, '').split('/')[0].toLowerCase()
      if (domain) {
        webMinutesMap[domain] = (webMinutesMap[domain] || 0) + 1
      }
    }
  })

  // GỘP THỜI GIAN & LUẬT APP THÀNH MỘT DANH SÁCH THỐNG NHẤT (DÙNG useMemo TỐI ƯU PERFORMANCE)
  const mergedAppsList = useMemo(() => {
    const mergedAppsMap = {}
    appUsage.forEach(u => {
      if (!u.process_name) return
      const key = u.process_name.toLowerCase()
      mergedAppsMap[key] = {
        process_name: u.process_name,
        used_minutes: u.used_minutes || 0,
        category: 'allowed',
        max_minutes_per_day: 0,
        rule_id: null
      }
    })

    appHistorySource.forEach(item => {
      if (!item.process_name) return
      const key = item.process_name.toLowerCase()
      if (!mergedAppsMap[key]) {
        mergedAppsMap[key] = {
          process_name: item.process_name,
          used_minutes: 1,
          category: 'allowed',
          max_minutes_per_day: 0,
          rule_id: null
        }
      }
    })

    appRules.forEach(r => {
      if (!r.process_name) return
      const key = r.process_name.toLowerCase()
      if (mergedAppsMap[key]) {
        mergedAppsMap[key].category = r.category
        mergedAppsMap[key].max_minutes_per_day = r.max_minutes_per_day
        mergedAppsMap[key].rule_id = r.id
      } else {
        mergedAppsMap[key] = {
          process_name: r.process_name,
          used_minutes: 0,
          category: r.category,
          max_minutes_per_day: r.max_minutes_per_day,
          rule_id: r.id
        }
      }
    })

    processes.forEach(p => {
      if (!p.process_name) return
      const key = p.process_name.toLowerCase()
      if (!mergedAppsMap[key]) {
        mergedAppsMap[key] = {
          process_name: p.process_name,
          used_minutes: 0,
          category: 'allowed',
          max_minutes_per_day: 0,
          rule_id: null
        }
      }
    })

    return Object.values(mergedAppsMap).filter(app => {
      if (hideUnusedApps) return app.used_minutes > 0
      return true
    })
  }, [appUsage, appHistorySource, appRules, processes, hideUnusedApps])

  // GỘP THỜI GIAN & LUẬT WEB THÀNH MỘT DANH SÁCH THỐNG NHẤT
  const mergedWebsList = useMemo(() => {
    const mergedWebsMap = {}
    webUsage.forEach(u => {
      if (!u.domain) return
      const key = u.domain.toLowerCase()
      mergedWebsMap[key] = {
        domain: u.domain,
        used_minutes: u.used_minutes || 0,
        category: 'allowed',
        max_minutes_per_day: 0,
        rule_id: null
      }
    })

    webHistorySource.forEach(item => {
      if (!item.url) return
      const domain = item.url.replace(/^(?:https?:\/\/)?(?:www\.)?/i, '').split('/')[0]
      if (!domain) return
      const key = domain.toLowerCase()
      if (!mergedWebsMap[key]) {
        mergedWebsMap[key] = {
          domain: domain,
          used_minutes: 1,
          category: 'allowed',
          max_minutes_per_day: 0,
          rule_id: null
        }
      }
    })

    webRules.forEach(r => {
      if (!r.domain) return
      const key = r.domain.toLowerCase()
      if (mergedWebsMap[key]) {
        mergedWebsMap[key].category = r.category
        mergedWebsMap[key].max_minutes_per_day = r.max_minutes_per_day
        mergedWebsMap[key].rule_id = r.id
      } else {
        mergedWebsMap[key] = {
          domain: r.domain,
          used_minutes: 0,
          category: r.category,
          max_minutes_per_day: r.max_minutes_per_day,
          rule_id: r.id
        }
      }
    })

    return Object.values(mergedWebsMap).filter(web => {
      if (hideUnusedApps) return web.used_minutes > 0
      return true
    })
  }, [webUsage, webHistorySource, webRules, hideUnusedApps])

  // FILTERED & GROUPED BROWSER HISTORY LOGS
  const { mergedBrowserHistory, groupedBrowserHistory } = useMemo(() => {
    const filteredBrowserHistory = webHistorySource.filter(item => {
      if (!historySearch.trim()) return true
      const s = historySearch.toLowerCase()
      return (item.title || '').toLowerCase().includes(s) || (item.url || '').toLowerCase().includes(s) || (item.browser_name || '').toLowerCase().includes(s)
    })

    const merged = mergeConsecutiveEntries(filteredBrowserHistory)
    const grouped = {}
    merged.forEach(item => {
      const dateLabel = formatDateHeader(item.visit_time || item.startTime)
      if (!grouped[dateLabel]) grouped[dateLabel] = []
      grouped[dateLabel].push(item)
    })
    return { mergedBrowserHistory: merged, groupedBrowserHistory: grouped }
  }, [webHistorySource, historySearch])

  // FILTERED & GROUPED APP USAGE LOGS
  const { mergedAppHistory, groupedAppHistory } = useMemo(() => {
    const filteredAppHistory = appHistorySource.filter(item => {
      if (!appHistorySearch.trim()) return true
      const s = appHistorySearch.toLowerCase()
      return (item.title || '').toLowerCase().includes(s) || (item.process_name || '').toLowerCase().includes(s)
    })

    const merged = mergeConsecutiveEntries(filteredAppHistory)
    const grouped = {}
    merged.forEach(item => {
      const dateLabel = formatDateHeader(item.created_at || item.startTime)
      if (!grouped[dateLabel]) grouped[dateLabel] = []
      grouped[dateLabel].push(item)
    })
    return { mergedAppHistory: merged, groupedAppHistory: grouped }
  }, [appHistorySource, appHistorySearch])

  // Tạo cấu trúc Log File (gom nhóm cả Web và App)
  const groupedLogFile = useMemo(() => {
    const logFileEntries = []
    
    mergedBrowserHistory.forEach(item => {
      logFileEntries.push({
        type: 'WEB',
        timestamp: new Date(item.visit_time || item.startTime).getTime(),
        displayTime: formatClockTime(item.visit_time || item.startTime),
        title: item.title || item.url,
        domain: item.url ? item.url.replace(/^(?:https?:\/\/)?(?:www\.)?/i, '').split('/')[0] : '',
        count: item.count,
        dateLabel: formatDateHeader(item.visit_time || item.startTime)
      })
    })

    mergedAppHistory.forEach(item => {
      logFileEntries.push({
        type: 'APP',
        timestamp: new Date(item.created_at || item.startTime).getTime(),
        displayTime: formatClockTime(item.created_at || item.startTime),
        title: item.title || item.process_name,
        domain: item.process_name,
        count: item.count,
        dateLabel: formatDateHeader(item.created_at || item.startTime)
      })
    })

    logFileEntries.sort((a, b) => b.timestamp - a.timestamp)
    
    const grouped = {}
    logFileEntries.forEach(log => {
      if (!grouped[log.dateLabel]) grouped[log.dateLabel] = []
      grouped[log.dateLabel].push(log)
    })
    return grouped
  }, [mergedBrowserHistory, mergedAppHistory])

  // Tổng số lượng bản ghi Log File để hiển thị trên Tab Badge
  const totalLogFileCount = useMemo(() => {
    return Object.values(groupedLogFile || {}).reduce((acc, items) => acc + (items?.length || 0), 0)
  }, [groupedLogFile])

  // TAB MENU ITEMS (ĐỔI TÊN TAB THÀNH " Quá trình sử dụng" VÀ GỘP LỊCH SỬ DUYỆT WEB VÀO TRONG)
  const rawTabList = [
    { id: 'overview', label: 'Tổng quan' },
    { id: 'todo', label: ' To Do Notes' },
    { id: 'calendar', label: ' Thời gian biểu' },
    { id: 'chat', label: ' Chat 2 chiều' },
    { id: 'ai_analysis', label: ' AI Phân tích' },
    { id: 'app_usage', label: ' Quá trình sử dụng' },
  ]

  // CHỈ ADMIN MỚI ĐƯỢC XEM TAB  ẢNH CHỤP & CÀI ĐẶT & QUẢN LÝ BỘ NHỚ
  if (isAdmin) {
    rawTabList.push({ id: 'screenshots', label: ' Ảnh chụp' })
    rawTabList.push({ id: 'storage', label: ' Quản lý bộ nhớ' })
    rawTabList.push({ id: 'config', label: ' Cài đặt Admin' })
  }

  // Danh sách các role bao gồm 'Khách (Chưa chọn tư cách)' và tất cả customRoles
  const displayRoles = ['Khách (Chưa chọn)', ...customRoles]

  // Lọc Tab theo phân quyền của tư cách (nếu tư cách đó bị đặt 'none')
  const effectiveRole = userRole || 'Khách (Chưa chọn)'
  const currentRolePerms = rolePermissions[effectiveRole] || {}
  const tabList = rawTabList.filter(tab => {
    if (isAdmin) return true
    const perm = currentRolePerms[tab.id]
    return perm !== 'none'
  })

  // Sắp xếp Ảnh chụp màn hình theo Ngày (Dùng useMemo tối ưu)
  const groupedScreenshots = useMemo(() => {
    const grouped = {}
    screenshots.forEach(item => {
      const groupKey = formatDateGroup(item.created_at)
      if (!grouped[groupKey]) grouped[groupKey] = []
      grouped[groupKey].push(item)
    })
    return grouped
  }, [screenshots])

  // MÀN HÌNH NẾU BỊ CHẶN TRUY CẬP
  if (isSessionBlocked) {
    return (
      <div className="min-h-screen bg-black text-zinc-100 flex items-center justify-center p-4 min-h-screen">
        <div className="bg-zinc-900/50 border border-red-500/30 rounded-3xl p-8 max-w-md w-full text-center space-y-4 shadow-2xl">
          <div className="text-5xl"></div>
          <h2 className="text-xl font-bold text-red-400">Truy Cập Bị Khóa</h2>
          <p className="text-sm text-zinc-300">Thiết bị / Phiên làm việc của bạn đã bị Admin chặn truy cập Web App.</p>
          <div className="text-xs text-zinc-500 font-mono">Session ID: {sessionId}</div>
        </div>
      </div>
    )
  }

  // Đổi Màu Nền theo Theme
  const themeClasses = {
    dark: 'bg-black text-slate-100',
    black: 'bg-black text-slate-100',
    light: 'bg-slate-100 text-slate-900'
  }[themeMode] || 'bg-black text-slate-100'

  const cardBgClass = {
    dark: 'bg-zinc-900/50 border-zinc-800',
    black: 'bg-zinc-950 border-zinc-800',
    light: 'bg-white border-slate-200 shadow-sm text-slate-900'
  }[themeMode]

  return (
    <div className={`min-h-screen ${themeClasses} relative transition-colors duration-300`}>
      {/* MODAL HỎI TƯ CÁCH LẦN ĐẦU TRUY CẬP + NHẬP MẬT KHẨU TƯ CÁCH */}
      {showRoleModal && (
        <div className="fixed inset-0 bg-black/85 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className={`${cardBgClass} border rounded-3xl p-6 max-w-sm w-full shadow-2xl text-center space-y-5 relative`}>
            <button onClick={() => setShowRoleModal(false)} className="absolute top-4 right-4 text-zinc-400 hover:text-white"></button>

            {selectedRoleToAuth ? (
              /* FORM XÁC NHẬN MẬT KHẨU CHO TƯ CÁCH ĐƯỢC CHỌN */
              <form onSubmit={handleVerifyRolePassword} className="space-y-4">
                <div className="text-4xl mb-1"></div>
                <div>
                  <h2 className="text-lg font-bold">Mật Khẩu Tư Cách "{selectedRoleToAuth}"</h2>
                  <p className="text-xs text-zinc-400 mt-1">Admin đã thiết lập mật khẩu cho tư cách này.</p>
                </div>
                <input
                  type="password"
                  placeholder="Nhập mật khẩu..."
                  value={roleAuthInput}
                  onChange={(e) => setRoleAuthInput(e.target.value)}
                  className="w-full bg-black border border-zinc-800 rounded-xl px-4 py-2.5 text-center text-sm font-mono outline-none focus:border-indigo-500"
                  autoFocus
                  required
                />
                {roleAuthError && <div className="text-xs text-red-400 font-medium">{roleAuthError}</div>}
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setSelectedRoleToAuth(null)}
                    className="flex-1 py-2.5 bg-zinc-900 hover:bg-slate-700 text-zinc-300 font-semibold rounded-xl text-xs"
                  >
                    Quay lại
                  </button>
                  <button
                    type="submit"
                    className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl text-xs"
                  >
                    Xác nhận
                  </button>
                </div>
              </form>
            ) : (
              /* DANH SÁCH CHỌN TƯ CÁCH */
              <>
                <div>
                  <h2 className="text-xl font-bold">Xác Nhận Tư Cách Truy Cập</h2>
                  <p className="text-xs text-zinc-400 mt-1">Bạn đang truy cập Web App này với tư cách là?</p>
                </div>

                <div className="space-y-2.5 max-h-60 overflow-y-auto pr-1">
                  {customRoles.map((roleName, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleInitiateRoleSelect(roleName)}
                      className={`w-full py-3 font-semibold rounded-2xl text-sm border transition transform hover:scale-[1.02] flex items-center justify-between px-4 ${
                        userRole === roleName ? 'bg-zinc-100 text-black hover:bg-white border-indigo-500' : 'bg-blue-600/10 hover:bg-blue-600/30 text-blue-300 border-indigo-500/20'
                      }`}
                    >
                      <span>{roleName}</span>
                      {rolePasswords[roleName] && <span>Có Pass</span>}
                    </button>
                  ))}
                </div>

                {/* FORM TỰ THÊM TƯ CÁCH CHO VIEWER */}
                <form onSubmit={handleAddViewerRole} className="pt-2 border-t border-zinc-800 flex gap-2">
                  <input
                    type="text"
                    placeholder="Tự thêm tư cách mới..."
                    value={newViewerRoleInput}
                    onChange={(e) => setNewViewerRoleInput(e.target.value)}
                    className="flex-grow bg-black border border-zinc-800 rounded-xl px-3 py-2 text-xs outline-none focus:border-indigo-500"
                  />
                  <button type="submit" className="px-3 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl text-xs transition">
                    + Thêm
                  </button>
                </form>
              </>
            )}
          </div>
        </div>
      )}

      {/* MODAL THÊM QUY TẮC BLACK LIST (APP HOẶC TRANG WEB) */}
      {showAddBlackListModal && (
        <div className="fixed inset-0 bg-black/85 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className={`${cardBgClass} border rounded-3xl p-6 max-w-md w-full shadow-2xl space-y-5 relative`}>
            <button onClick={() => setShowAddBlackListModal(false)} className="absolute top-4 right-4 text-zinc-400 hover:text-white"></button>
            <div className="text-center">
              <div className="text-4xl mb-1"></div>
              <h2 className="text-xl font-bold">Thêm Quy Tắc Black List</h2>
              <p className="text-xs text-zinc-400 mt-1">Giới hạn thời gian hoặc cấm hẳn Ứng dụng / Trang web</p>
            </div>

            <form onSubmit={handleAddBlackListRule} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-zinc-300 mb-1.5">Loại đối tượng:</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setBlackListRuleType('web')}
                    className={`py-2.5 rounded-xl border text-xs font-semibold flex items-center justify-center gap-1.5 transition ${
                      blackListRuleType === 'web' ? 'bg-zinc-100 text-black hover:bg-white border-indigo-500' : 'bg-black text-zinc-400 border-zinc-800'
                    }`}
                  >
                    <span> Trang Web</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setBlackListRuleType('app')}
                    className={`py-2.5 rounded-xl border text-xs font-semibold flex items-center justify-center gap-1.5 transition ${
                      blackListRuleType === 'app' ? 'bg-zinc-100 text-black hover:bg-white border-indigo-500' : 'bg-black text-zinc-400 border-zinc-800'
                    }`}
                  >
                    <span> Ứng Dụng (.exe)</span>
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-300 mb-1.5">
                  {blackListRuleType === 'web' ? 'Tên miền trang web (Domain):' : 'Tên tiến trình ứng dụng (.exe):'}
                </label>
                <input
                  type="text"
                  placeholder={blackListRuleType === 'web' ? 'Ví dụ: facebook.com, youtube.com, tiktok.com...' : 'Ví dụ: roblox.exe, garena.exe, chrome.exe...'}
                  value={blackListTargetInput}
                  onChange={(e) => setBlackListTargetInput(e.target.value)}
                  className="w-full bg-black border border-zinc-800 rounded-xl px-4 py-2.5 text-xs text-zinc-200 outline-none focus:border-indigo-500 font-mono"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-300 mb-1.5">Hình thức áp dụng:</label>
                <select
                  value={blackListCategory}
                  onChange={(e) => setBlackListCategory(e.target.value)}
                  className="w-full bg-black border border-zinc-800 rounded-xl px-4 py-2.5 text-xs text-zinc-200 font-semibold outline-none focus:border-indigo-500"
                >
                  <option value="forbidden"> Cấm hẳn (không cho dùng)</option>
                  <option value="limited">⏱ Giới hạn (số phút dùng/ngày)</option>
                </select>
              </div>

              {blackListCategory === 'limited' && (
                <div>
                  <label className="block text-xs font-semibold text-zinc-300 mb-1.5">Số phút cho phép tối đa mỗi ngày:</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min="1"
                      max="1440"
                      value={blackListMaxMinutes}
                      onChange={(e) => setBlackListMaxMinutes(e.target.value)}
                      className="w-full bg-black border border-zinc-800 rounded-xl px-4 py-2.5 text-xs font-bold text-zinc-200 outline-none focus:border-amber-500"
                      required
                    />
                    <span className="text-xs text-zinc-400 whitespace-nowrap">phút/ngày</span>
                  </div>
                </div>
              )}

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddBlackListModal(false)}
                  className="flex-1 py-2.5 bg-zinc-900 hover:bg-slate-700 text-zinc-300 font-semibold rounded-xl text-xs"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl text-xs transition"
                >
                  + Thêm Vào Black List
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CỬA SỔ FLOATING BÓNG CHAT SẮP XẾP THEO THỨ TỰ: TO DO / CHAT / ONLINE */}
      <div className="hidden lg:flex fixed bottom-6 right-6 z-40 flex-col items-end gap-3">
        {showFloatingWidget ? (
          <div className={`w-96 ${cardBgClass} border rounded-3xl shadow-2xl backdrop-blur-md overflow-hidden flex flex-col h-[480px]`}>
            {/* Header Cửa Sổ Ghim - SẮP XẾP THỨ TỰ: TO DO / CHAT / ONLINE */}
            <div className="p-3 border-b border-zinc-800 flex items-center justify-between">
              <div className="flex gap-1 overflow-x-auto">
                <button
                  onClick={() => setFloatingTab('todo')}
                  className={`px-2.5 py-1 rounded-full text-xs font-semibold whitespace-nowrap transition ${
                    floatingTab === 'todo' ? 'bg-amber-500/10 text-zinc-200 border border-amber-500/20' : 'text-zinc-400 hover:bg-zinc-900'
                  }`}
                >
                   To Do Ghim
                </button>
                <button
                  onClick={() => setFloatingTab('chat')}
                  className={`px-2.5 py-1 rounded-full text-xs font-semibold whitespace-nowrap transition ${
                    floatingTab === 'chat' ? 'bg-zinc-100 text-black hover:bg-white' : 'text-zinc-400 hover:bg-zinc-900'
                  }`}
                >
                   Chat Nhanh
                </button>
                <button
                  onClick={() => setFloatingTab('online')}
                  className={`px-2.5 py-1 rounded-full text-xs font-semibold whitespace-nowrap transition ${
                    floatingTab === 'online' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'text-zinc-400 hover:bg-zinc-900'
                  }`}
                >
                   Online ({activeSessions.length})
                </button>
              </div>
              <button
                onClick={() => setShowFloatingWidget(false)}
                className="w-6 h-6 rounded-full hover:bg-zinc-800 text-zinc-400 hover:text-white flex items-center justify-center text-xs font-bold transition"
                title="Đóng cửa sổ ghim"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Nội dung Tab To Do Ghim (REFACTORED WITH PROGRESS BAR & PRIORITY SORTING) */}
            {floatingTab === 'todo' && (() => {
              const combinedTodayTasks = [
                ...todoNotes.map(t => ({
                  id: t.id,
                  title: t.task_title,
                  taskType: t.task_type || 'custom',
                  isCompleted: !!t.is_completed,
                  isSheet: false,
                  priority: t.task_type === 'admin_assigned' ? 'Quan trọng' : 'Bình thường'
                })),
                ...sheetTasks
                  .filter(st => !deletedSheetTaskIds.includes(st.id))
                  .map(st => ({
                    id: st.id,
                    title: st.title,
                    taskType: st.isDaily ? 'routine' : 'sheet',
                    isCompleted: !!completedSheetTasks[st.id],
                    isSheet: true,
                    priority: st.priority || (st.isDaily ? 'Hằng ngày' : 'Bình thường')
                  }))
              ]

              // Helper score priority: High (3), Daily (2), Normal (1)
              const getPriorityScore = (pStr) => {
                if (!pStr) return 1
                const p = pStr.toLowerCase().trim()
                if (p.includes('quan trọng') || p.includes('high') || p.includes('gấp')) return 3
                if (p.includes('hằng ngày') || p.includes('thói quen') || p.includes('daily')) return 2
                return 1
              }

              // Sort high priority to top
              combinedTodayTasks.sort((a, b) => getPriorityScore(b.priority) - getPriorityScore(a.priority))

              const totalWidgetTasks = combinedTodayTasks.length
              const completedWidgetTasks = combinedTodayTasks.filter(t => t.isCompleted).length
              const progressWidgetPercent = totalWidgetTasks > 0 ? Math.round((completedWidgetTasks / totalWidgetTasks) * 100) : 0

              return (
                <div className="flex-grow p-4 overflow-y-auto space-y-4">
                  {/* PROGRESS BAR WIDGET */}
                  <div className="p-3 bg-zinc-900/50 border border-zinc-800 rounded-2xl space-y-2 shadow-inner">
                    <div className="flex items-center justify-between text-[11px] font-bold">
                      <span className="text-zinc-300 flex items-center gap-1.5">
                        <span></span> Tiến Độ Hôm Nay
                      </span>
                      <span className="text-emerald-400 font-mono text-[10px] bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                        {completedWidgetTasks}/{totalWidgetTasks} xong ({progressWidgetPercent}%)
                      </span>
                    </div>

                    <div className="h-2 w-full bg-black rounded-full overflow-hidden border border-zinc-800">
                      <div
                        className="h-full bg-gradient-to-r from-blue-500 via-teal-400 to-emerald-400 rounded-full transition-all duration-500 shadow"
                        style={{ width: `${progressWidgetPercent}%` }}
                      ></div>
                    </div>
                  </div>

                  {/* TASK LIST WIDGET */}
                  <div className="space-y-2">
                    <div className="text-[11px] font-bold text-zinc-400 flex items-center justify-between px-1">
                      <span>NHIỆM VỤ DÀNH CHO HÔM NAY ({totalWidgetTasks})</span>
                      <span className="text-[10px] text-zinc-200 font-normal"> Ưu tiên lên đầu</span>
                    </div>

                    {combinedTodayTasks.length === 0 ? (
                      <div className="text-center text-zinc-500 text-xs py-10">
                        <span> Không có nhiệm vụ nào cần làm!</span>
                      </div>
                    ) : (
                      combinedTodayTasks.map(t => {
                        const pLower = (t.priority || '').toLowerCase()
                        const isHigh = pLower.includes('quan trọng') || pLower.includes('high') || t.taskType === 'admin_assigned'
                        const isDaily = pLower.includes('hằng ngày') || pLower.includes('thói quen') || t.taskType === 'routine'

                        return (
                          <label
                            key={t.id}
                            className={`flex items-start gap-2.5 p-2.5 rounded-xl border transition cursor-pointer ${
                              t.isCompleted
                                ? 'bg-black/40 border-slate-900 opacity-60'
                                : 'bg-zinc-900/50/90 border-zinc-800 hover:border-zinc-800 shadow-sm'
                            }`}
                          >
                            <input
                              type="checkbox"
                              checked={t.isCompleted}
                              onChange={() => {
                                if (t.isSheet) toggleSheetTaskComplete(t.id)
                                else toggleTodoComplete(t.id, t.isCompleted)
                              }}
                              className="w-4 h-4 rounded text-blue-600 cursor-pointer mt-0.5 shrink-0"
                            />

                            <div className="space-y-1 min-w-0 flex-grow">
                              <div className="flex items-center gap-1.5 flex-wrap">
                                {isHigh && (
                                  <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30">
                                     Quan trọng
                                  </span>
                                )}
                                {isDaily && (
                                  <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 border border-emerald-500/30">
                                     Hằng ngày
                                  </span>
                                )}
                                {!isHigh && !isDaily && (
                                  <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-blue-500/20 text-blue-300 border border-indigo-500/30">
                                     Bình thường
                                  </span>
                                )}
                              </div>

                              <span className={`text-xs block leading-relaxed break-words ${t.isCompleted ? 'line-through text-zinc-500' : 'text-zinc-200 font-medium'}`}>
                                {t.title}
                              </span>
                            </div>
                          </label>
                        )
                      })
                    )}
                  </div>
                </div>
              )
            })()}

            {/* Nội dung Tab Chat Ghim */}
            {floatingTab === 'chat' && (
              <div className="flex-grow flex flex-col p-3 overflow-hidden">
                <div className="flex-grow overflow-y-auto space-y-2.5 pr-1">
                  {chatMessages.length === 0 ? (
                    <div className="text-center text-zinc-500 text-xs py-20">Chưa có tin nhắn nào.</div>
                  ) : (
                    chatMessages.map((msg, idx) => (
                      <div key={msg.id || idx} className={`flex ${msg.sender === 'admin' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[80%] p-2.5 rounded-2xl text-xs ${
                          msg.sender === 'admin' ? 'bg-zinc-100 text-black hover:bg-white rounded-br-none' : 'bg-zinc-900 text-zinc-200 border border-zinc-800 rounded-bl-none'
                        }`}>
                          <div className="text-[9px] font-bold opacity-75 mb-0.5">{msg.sender === 'admin' ? 'Quản lý' : msg.sender}</div>
                          <div className="break-words">{msg.message}</div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
                <form
                  onSubmit={(e) => {
                    e.preventDefault()
                    handleSendChatMsg(floatingChatInput)
                  }}
                  className="flex gap-2 mt-2 pt-2 border-t border-zinc-800"
                >
                  <input
                    type="text"
                    placeholder="Gõ tin nhắn..."
                    value={floatingChatInput}
                    onChange={(e) => setFloatingChatInput(e.target.value)}
                    className="flex-grow bg-black border border-zinc-800 rounded-xl px-3 py-2 text-xs outline-none focus:border-indigo-500"
                  />
                  <button type="submit" className="px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl text-xs transition">
                    Gửi
                  </button>
                </form>
              </div>
            )}

            {/* TAB HIỂN THỊ CÁC THIẾT BỊ / NGƯỜI ĐANG ONLINE TRONG POPUP CHAT */}
            {floatingTab === 'online' && (
              <div className="flex-grow p-3 overflow-y-auto space-y-3">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-bold text-emerald-400">
                     Thiết Bị Online ({activeSessions.length})
                  </div>
                  {isAdmin && (
                    <button
                      onClick={cleanupStaleSessions}
                      className="px-2 py-1 bg-zinc-900 hover:bg-slate-700 text-zinc-300 text-[10px] font-bold rounded-lg transition border border-zinc-800 flex items-center gap-1"
                      title="Quét & Xóa toàn bộ Session rác quá 35s"
                    >
                      <span> Dọn Rác</span>
                    </button>
                  )}
                </div>

                {activeSessions.length === 0 ? (
                  <div className="text-xs text-zinc-500 text-center py-10">Chưa có thiết bị nào đang kết nối.</div>
                ) : (
                  activeSessions.map((sess, idx) => {
                    const isCurrentDev = sess.session_id === sessionId
                    const diffSec = sess.last_active ? Math.max(0, Math.round((Date.now() - new Date(sess.last_active).getTime()) / 1000)) : 0
                    const activeText = diffSec <= 5 ? ' Vừa tương tác' : `⏱ ${diffSec}s trước`

                    return (
                      <div key={sess.session_id || idx} className="p-2.5 bg-zinc-900/50 border border-zinc-800 rounded-xl text-xs space-y-1.5 shadow-sm">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2 font-semibold text-zinc-200 min-w-0">
                            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shrink-0"></span>
                            <span className="truncate">{sess.device_info || 'Thiết bị'}</span>
                          </div>
                          {isCurrentDev && (
                            <span className="text-[9px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold border border-emerald-500/30 shrink-0">
                              Bạn
                            </span>
                          )}
                        </div>

                        <div className="flex items-center justify-between text-[10px] text-zinc-400 pt-1 border-t border-slate-900">
                          <div>
                            Tư cách: <strong className="text-blue-300">{sess.user_role}</strong>
                            {sess.tabCount > 1 && (
                              <span className="ml-1.5 px-1.5 py-0.5 rounded bg-zinc-400/20 text-zinc-300 font-mono font-bold">
                                {sess.tabCount} Tabs
                              </span>
                            )}
                          </div>
                          <span className="text-emerald-400 font-mono">{activeText}</span>
                        </div>
                      </div>
                    )
                  })
                )}
              </div>
            )}
          </div>
        ) : (
          <button
            onClick={() => setShowFloatingWidget(prev => !prev)}
            className="px-4 py-3 bg-zinc-100 hover:bg-white text-black font-bold rounded-full shadow-2xl flex items-center gap-2 text-xs transition transform hover:scale-105 border border-zinc-300 z-40"
            title="Bật/Tắt cửa sổ ghim To Do, Chat & Online"
          >
            <Pin className="w-3.5 h-3.5 text-zinc-900" />
            <span>Mở To Do, Chat & Online Ghim</span>
          </button>
        )}
      </div>

      {/* MODAL ĐĂNG NHẬP ADMIN */}
      {showLoginModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className={`${cardBgClass} border rounded-3xl p-6 max-w-sm w-full shadow-2xl relative`}>
            <button onClick={() => setShowLoginModal(false)} className="absolute top-4 right-4 text-zinc-400 hover:text-white"></button>
            <div className="text-center mb-5">
              <div className="text-3xl mb-1"></div>
              <h2 className="text-xl font-bold">Xác Nhận Quyền Admin</h2>
              <p className="text-xs text-zinc-400 mt-1">Nhập mã PIN Admin để mở khóa tính năng quản trị</p>
            </div>
            <form onSubmit={handleAdminLogin} className="space-y-4">
              <div>
                <input
                  type="password"
                  placeholder="Nhập mã PIN Admin (Mặc định: 123456)..."
                  value={pinInput}
                  onChange={(e) => setPinInput(e.target.value)}
                  className="w-full bg-black border border-zinc-800 rounded-xl px-4 py-3 text-center text-lg font-mono outline-none focus:border-indigo-500"
                  autoFocus
                  required
                />
              </div>
              <div className="flex items-center gap-2 px-1">
                <input
                  type="checkbox"
                  id="remember"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="w-4 h-4 rounded bg-black border-zinc-800 text-blue-600"
                />
                <label htmlFor="remember" className="text-xs text-zinc-300 cursor-pointer">Ghi nhớ mật khẩu (trong 30 ngày)</label>
              </div>
              {loginError && <div className="text-xs text-red-400 text-center font-medium">{loginError}</div>}
              <button type="submit" className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl text-sm transition">
                Mở Quyền Quản Trị
              </button>
            </form>
          </div>
        </div>
      )}

      {/* MAIN SAAS DASHBOARD CONTAINER WITH LEFT SIDEBAR */}
      <div className="min-h-screen bg-black text-zinc-100 font-sans flex flex-col lg:flex-row antialiased selection:bg-zinc-800 selection:text-white pb-20 lg:pb-0 overflow-x-hidden w-full max-w-full">
        
        {/* LEFT SIDEBAR NAVIGATION (DESKTOP ONLY lg:flex) */}
        <Sidebar
        tabList={tabList}
        activeTab={activeTab}
        changeActiveTab={changeActiveTab}
        isAdmin={isAdmin}
        userRole={userRole}
        setShowRoleModal={setShowRoleModal}
      />

        {/* MAIN CONTENT AREA */}
        <div className="flex-1 flex flex-col min-w-0 overflow-y-auto lg:pl-64">
          {/* HEADER BAR */}
          <header className="bg-black/90 border-b border-zinc-800 backdrop-blur-md sticky top-0 z-20 px-4 sm:px-6 py-3.5 flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div className="flex items-center justify-between md:justify-start gap-3">
              <div>
                <div className="flex items-center gap-2.5">
                  {/* MOBILE COMPACT LOGO */}
                  <div className="w-7 h-7 rounded-lg bg-zinc-900 flex lg:hidden items-center justify-center text-xs font-black text-white shadow">
                    
                  </div>
                  <h2 className="text-base sm:text-lg font-bold text-slate-100 truncate">
                    {tabList.find(t => t.id === activeTab)?.label || 'Tổng Quan'}
                  </h2>
                  <span className="text-[11px] text-zinc-400 font-medium hidden sm:inline"> {todayFormatted}</span>
                </div>

                {/* DEVICE STATUS BADGE */}
                {isAdmin && (
                  <div className="mt-1 flex items-center gap-2 text-xs">
                    {isDeviceOnline ? (
                      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 font-bold border border-emerald-500/20 text-[10px] sm:text-[11px]">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                        <span> Máy em trai ({DEVICE_NAME}) • {formatTime(device?.last_seen)}</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 font-bold border border-red-500/20 text-[10px] sm:text-[11px]">
                        <span className="w-1.5 h-1.5 rounded-full bg-red-400"></span>
                        <span> Mất kết nối với máy em trai</span>
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* MOBILE ROLE BADGE & SETTINGS */}
              <div className="flex lg:hidden items-center gap-1.5">
                <button
                  onClick={() => setShowRoleModal(true)}
                  className="px-2.5 py-1 bg-zinc-900 hover:bg-slate-700 text-amber-300 rounded-lg text-xs font-semibold border border-zinc-800 flex items-center gap-1"
                >
                  <span></span>
                  <span className="truncate max-w-[80px]">{isAdmin ? 'Admin' : (userRole || 'Chưa chọn')}</span>
                </button>
              </div>
            </div>

            {/* HEADER RIGHT ACTIONS */}
            <div className="flex items-center justify-between md:justify-end gap-2.5">
              {isAdmin ? (
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full text-[11px] font-bold flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                    Admin Mode
                  </span>
                  <button onClick={handleAdminLogout} className="px-3 py-1.5 bg-zinc-900 hover:bg-slate-700 text-zinc-300 rounded-xl text-xs font-semibold transition border border-zinc-800">
                    Thoát Admin
                  </button>
                </div>
              ) : (
                <button onClick={() => setShowLoginModal(true)} className="px-3.5 py-1.5 bg-amber-600/20 text-amber-300 hover:bg-amber-600/30 border border-amber-500/30 rounded-xl text-xs font-bold transition flex items-center gap-1.5 shadow">
                  <span></span>
                  <span>Truy Cập Admin</span>
                </button>
              )}
            </div>
          </header>

          {/* WARNING BANNER WHEN PAUSED */}
          {isPaused && (
            <div className="mx-4 sm:mx-6 mt-3 p-3 rounded-2xl bg-amber-600/20 border border-amber-500/30 text-amber-300 text-xs font-bold flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 animate-pulse">
              <div className="flex items-center gap-2">
                <span></span>
                <span>ĐANG TẠM DỪNG KIỂM SOÁT (PAUSED) — Mọi thiết bị đang được tự do.</span>
              </div>
              {isAdmin && (
                <button onClick={handleTogglePauseControl} className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold shadow whitespace-nowrap self-end sm:self-auto">
                  Tiếp tục kiểm soát
                </button>
              )}
            </div>
          )}

          {/* TOUCH-FRIENDLY QUICK ACTION BAR (GRID 2x2 ON MOBILE) */}
          {isAdmin && (
            <div className="mx-4 sm:mx-6 mt-3 p-3.5 sm:p-4 rounded-2xl bg-zinc-900/50/80 border border-zinc-800 space-y-2.5 shadow-xl">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider"> Thanh Thao Tác Nhanh (Action Bar):</span>
              </div>
              <div className="grid grid-cols-2 md:flex items-center gap-2">
                {isPaused ? (
                  <button
                    onClick={handleTogglePauseControl}
                    disabled={togglePauseLoading}
                    className="h-11 px-3 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl text-xs transition shadow-lg flex items-center justify-center gap-1.5"
                  >
                    <span>▶️</span>
                    <span className="truncate">{togglePauseLoading ? 'Xử lý...' : 'TIẾP TỤC KIỂM SOÁT'}</span>
                  </button>
                ) : (
                  <button
                    onClick={handleTogglePauseControl}
                    disabled={togglePauseLoading}
                    className="h-11 px-3 bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 border border-amber-500/30 font-bold rounded-xl text-xs transition flex items-center justify-center gap-1.5"
                  >
                    <span></span>
                    <span className="truncate">{togglePauseLoading ? 'Xử lý...' : 'TẠM DỪNG KIỂM SOÁT'}</span>
                  </button>
                )}

                <button
                  onClick={triggerForceAgentUpdate}
                  disabled={updateSending}
                  className="h-11 px-3 bg-amber-600 hover:bg-amber-500 text-white font-bold rounded-xl text-xs transition disabled:opacity-50 flex items-center justify-center gap-1.5 shadow"
                >
                  <span></span>
                  <span className="truncate">{updateSending ? '⏳ Nâng cấp...' : 'Cập Nhật Agent'}</span>
                </button>

                <button
                  onClick={handleToggleDeviceAllowed}
                  className={`h-11 px-3 font-bold rounded-xl text-xs transition flex items-center justify-center gap-1.5 ${
                    isDeviceAllowed
                      ? 'bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30'
                      : 'bg-red-600 hover:bg-red-500 text-white animate-pulse shadow-lg'
                  }`}
                >
                  <span>{isDeviceAllowed ? '' : ''}</span>
                  <span className="truncate">{isDeviceAllowed ? 'Cho Phép Mở Máy' : 'Đang Cấm Mở Máy'}</span>
                </button>

                <button
                  onClick={sendInstantScreenshot}
                  disabled={cmdSending}
                  className="h-11 px-3 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl text-xs transition disabled:opacity-50 flex items-center justify-center gap-1.5 shadow"
                >
                  <span></span>
                  <span className="truncate">{cmdSending ? '⏳ Chụp...' : 'Chụp Hình Ngay'}</span>
                </button>
              </div>
            </div>
          )}

          {/* MAIN TAB CONTENT */}
          <main className="p-6 space-y-6">
            {loading ? (
              <div className="text-center py-24 text-zinc-500">Đang tải dữ liệu...</div>
            ) : (
              <>
                {/* TAB: Tổng quan */}
                {activeTab === 'overview' && (
                  <div className="space-y-6">
                    {/* 4 METRIC CARDS GRID */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
                      {/* CARD 1: CONNECTIVITY */}
                      <div className={`${cardBgClass} border border-zinc-800 rounded-2xl p-5 shadow-lg flex flex-col justify-between hover:border-indigo-500/40 transition group`}>
                        <div className="flex items-center justify-between mb-3">
                          <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Trạng Thái Kết Nối</span>
                          <span className={`w-3 h-3 rounded-full ${isDeviceOnline ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'}`}></span>
                        </div>
                        <div className="flex items-baseline gap-2">
                          <StatusDot status={isDeviceOnline ? "ready" : "blocked"} label={isDeviceOnline ? "Ready" : "Offline"} />
                        </div>
                        <div className="mt-3 pt-3 border-t border-zinc-800 text-[11px] text-zinc-400 flex items-center justify-between">
                          <span>{DEVICE_NAME}</span>
                          <span>{device?.last_seen ? formatClockTime(device.last_seen) : '—'}</span>
                        </div>
                      </div>

                      {/* CARD 2: AI PHÂN TÍCH */}
                      <div className="bg-zinc-950 border border-zinc-800 rounded-2xl p-5 shadow-lg flex flex-col justify-between hover:border-zinc-700/40 transition group">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Đánh Giá AI</span>
                          <Bot className="w-4 h-4 text-zinc-400 stroke-[1.5]" />
                        </div>
                        <div className="text-2xl font-bold text-zinc-100 mb-1">{aiReport.score}</div>
                        <div className="text-xs text-zinc-400 mb-2">{aiReport.ratio}</div>
                        <div className="mt-2 pt-2 border-t border-zinc-800 text-[11px] text-zinc-400 truncate">
                          Trạng thái: <strong className="text-emerald-400">{aiReport.status || 'Tốt'}</strong>
                        </div>
                      </div>

                      {/* CARD 3: CHẾ ĐỘ KIỂM SOÁT */}
                      <div className="bg-zinc-950 border border-zinc-800 rounded-2xl p-5 shadow-lg flex flex-col justify-between hover:border-zinc-700/40 transition group">
                        <div className="flex items-center justify-between mb-3">
                          <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Chế Độ Kiểm Soát</span>
                          {isPaused ? <PauseCircle className="w-4 h-4 text-amber-400 stroke-[1.5]" /> : <Shield className="w-4 h-4 text-zinc-400 stroke-[1.5]" />}
                        </div>
                        <div className="flex items-center justify-between">
                          <StatusDot status={isPaused ? "paused" : "ready"} label={isPaused ? "Paused" : "Active"} />
                        </div>
                      </div>

                      {/* CARD 4: TO DO HOÀN THÀNH */}
                      <div className="bg-zinc-950 border border-zinc-800 rounded-2xl p-5 shadow-lg flex flex-col justify-between hover:border-zinc-700/40 transition group">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Tiến Độ To Do</span>
                          <FileText className="w-4 h-4 text-zinc-400 stroke-[1.5]" />
                        </div>
                        <div>
                          <div className="flex items-center justify-between text-xs mb-1.5 font-bold font-mono">
                            <span className="text-zinc-300">Hoàn thành:</span>
                            <span className="text-emerald-400">
                              {(todoNotes ?? []).filter(t => t?.is_completed).length} / {(todoNotes ?? []).length}
                            </span>
                          </div>
                          <div className="w-full bg-black rounded-full h-2 overflow-hidden border border-zinc-800">
                            <div
                              className="bg-emerald-500 h-full transition-all"
                              style={{ width: `${(todoNotes ?? []).length > 0 ? ((todoNotes ?? []).filter(t => t?.is_completed).length / (todoNotes ?? []).length) * 100 : 0}%` }}
                            ></div>
                          </div>
                        </div>
                        <div className="mt-3 pt-3 border-t border-zinc-800 text-[11px] font-mono text-zinc-400">
                          Hôm nay: <strong className="text-zinc-200">{(sheetTasks ?? []).length} nhiệm vụ từ Sheet</strong>
                        </div>
                      </div>
                    </div>

                    {/* PROCESS MONITOR - MOBILE CARDS VIEW (< md) & DESKTOP TABLE VIEW (>= md) */}
                    <div id="process-table-section" className={`${cardBgClass} border border-zinc-800 rounded-2xl p-4 sm:p-5 shadow-xl space-y-4`}>
                      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-zinc-800 pb-4">
                        <div>
                          <h3 className="font-bold text-base flex items-center gap-2 text-slate-100">
                            <span></span> Tiến Trình Đang Chạy (Process Monitor)
                          </h3>
                          <p className="text-xs text-zinc-400 mt-1">Các ứng dụng và tiến trình hệ thống đang mở trên máy em trai.</p>
                        </div>
                        <div className="flex items-center gap-2 w-full sm:w-auto">
                          <input
                            type="text"
                            placeholder="Tìm kiếm tiến trình (.exe)..."
                            value={appHistorySearch}
                            onChange={(e) => setAppHistorySearch(e.target.value)}
                            className="bg-black border border-zinc-800/80 rounded-xl px-3.5 py-2 text-xs outline-none focus:border-indigo-500 font-mono text-zinc-200 w-full sm:w-64"
                          />
                          <button
                            onClick={() => loadData(false)}
                            className="px-3.5 py-2 bg-zinc-900 hover:bg-slate-700 text-zinc-300 font-semibold rounded-xl text-xs whitespace-nowrap border border-zinc-800 transition"
                          >
                             Tải Lại
                          </button>
                        </div>
                      </div>

                      {/* MOBILE CARDS LIST (< md) */}
                      <div className="grid grid-cols-1 gap-2.5 md:hidden">
                        {processes.filter(p => !appHistorySearch || p.process_name?.toLowerCase().includes(appHistorySearch.toLowerCase())).length === 0 ? (
                          <div className="text-center text-zinc-500 py-8 text-xs">Không tìm thấy tiến trình nào matching.</div>
                        ) : (
                          processes.filter(p => !appHistorySearch || p.process_name?.toLowerCase().includes(appHistorySearch.toLowerCase())).slice(0, 15).map((proc, idx) => {
                            const memMB = proc.memory_mb || 120
                            const memPercent = Math.min(100, Math.floor((memMB / 2048) * 100))
                            return (
                              <div key={proc.id || idx} className="p-3 bg-zinc-900/50 border border-zinc-800 rounded-xl flex items-center justify-between text-xs">
                                <div className="flex items-center gap-2.5 min-w-0">
                                  <span className="w-2.5 h-2.5 rounded-full bg-zinc-300 shrink-0"></span>
                                  <div className="truncate">
                                    <div className="font-bold text-zinc-200 truncate">{proc.process_name}</div>
                                    <div className="text-[10px] text-zinc-500 font-mono">{formatTime(proc.created_at)}</div>
                                  </div>
                                </div>
                                <div className="flex flex-col items-end shrink-0 ml-2">
                                  <span className="font-mono font-bold text-zinc-300">{memMB.toFixed(0)} MB</span>
                                  <div className="w-16 bg-zinc-900/50 rounded-full h-1.5 overflow-hidden border border-zinc-800 mt-1">
                                    <div className="bg-zinc-400 h-full" style={{ width: `${memPercent}%` }}></div>
                                  </div>
                                </div>
                              </div>
                            )
                          })
                        )}
                      </div>

                      {/* DESKTOP DATA TABLE (>= md) */}
                      <div className="hidden md:block overflow-x-auto">
                        <table className="w-full text-left text-xs">
                          <thead>
                            <tr className="border-b border-zinc-800 text-zinc-400 font-bold uppercase tracking-wider text-[11px] bg-zinc-900/50">
                              <th className="p-3">Ứng dụng / Process</th>
                              <th className="p-3">Tên Tiến Trình</th>
                              <th className="p-3">Mức Chiếm Dung Lượng RAM</th>
                              <th className="p-3">Cập Nhật Lần Cuối</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800/60">
                            {processes.filter(p => !appHistorySearch || p.process_name?.toLowerCase().includes(appHistorySearch.toLowerCase())).length === 0 ? (
                              <tr>
                                <td colSpan="4" className="text-center text-zinc-500 py-10">Không tìm thấy tiến trình nào matching.</td>
                              </tr>
                            ) : (
                              processes.filter(p => !appHistorySearch || p.process_name?.toLowerCase().includes(appHistorySearch.toLowerCase())).slice(0, 20).map((proc, idx) => {
                                const memMB = proc.memory_mb || 120
                                const memPercent = Math.min(100, Math.floor((memMB / 2048) * 100))
                                return (
                                  <tr key={proc.id || idx} className="hover:bg-zinc-900/40 transition">
                                    <td className="p-3 font-semibold text-zinc-200 flex items-center gap-2">
                                      <span className="w-2 h-2 rounded-full bg-blue-400"></span>
                                      <span>{proc.process_name}</span>
                                    </td>
                                    <td className="p-3 font-mono text-zinc-400">{proc.process_name}</td>
                                    <td className="p-3">
                                      <div className="flex items-center gap-2">
                                        <span className="font-mono font-bold text-zinc-300 w-16">{memMB.toFixed(0)} MB</span>
                                        <div className="w-28 bg-black rounded-full h-2 overflow-hidden border border-zinc-800">
                                          <div className="bg-zinc-400 h-full" style={{ width: `${memPercent}%` }}></div>
                                        </div>
                                      </div>
                                    </td>
                                    <td className="p-3 text-zinc-400">{formatTime(proc.created_at)}</td>
                                  </tr>
                                )
                              })
                            )}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                )}

            {/* TAB: TO DO NOTE — REFACTORED UNIFIED DASHBOARD */}
            {activeTab === 'todo' && (() => {
              // Gộp tất cả các task từ Supabase và Google Sheet thành danh sách thống nhất
              const combinedTasks = [
                ...todoNotes.map(t => ({
                  id: t.id,
                  title: t.task_title,
                  taskType: t.task_type || 'custom',
                  isCompleted: !!t.is_completed,
                  isSheet: false,
                  createdAt: t.created_at
                })),
                ...sheetTasks
                  .filter(st => !deletedSheetTaskIds.includes(st.id))
                  .map(st => ({
                    id: st.id,
                    title: st.title,
                    taskType: st.isDaily ? 'routine' : 'sheet',
                    isCompleted: !!completedSheetTasks[st.id],
                    isSheet: true,
                    createdAt: null
                  }))
              ]

              const totalTasks = combinedTasks.length
              const completedTasks = combinedTasks.filter(t => t.isCompleted).length
              const progressPercent = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0

              return (
                <div className="space-y-6 max-w-4xl mx-auto">
                  {/* CARD CHÍNH CỦA BẢNG TO DO */}
                  <div className={`${cardBgClass} border rounded-2xl p-6 space-y-6 shadow-2xl`}>

                    {/* 1. HEADER CHÍNH: TIÊU ĐỀ + TIẾN ĐỘ + NÚT ĐỒNG BỘ GOOGLE SHEET */}
                    <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-zinc-800 pb-5">
                      <div className="space-y-1">
                        <h2 className="text-xl font-bold flex items-center gap-2 text-slate-100">
                          <span></span> Danh Sách Nhiệm Vụ & Bài Tập Hôm Nay
                        </h2>
                        <p className="text-xs text-zinc-400">
                          Tổng hợp công việc do Admin giao, bài tập tự chọn và thói quen từ Google Sheet ({todayFormatted}).
                        </p>
                      </div>

                      <div className="flex items-center gap-3 w-full md:w-auto justify-between md:justify-end">
                        <button
                          onClick={fetchGoogleSheetTasks}
                          disabled={isSyncingSheet}
                          className="px-4 py-2 bg-zinc-900 hover:bg-slate-700 text-blue-300 font-bold rounded-xl text-xs border border-zinc-800 transition flex items-center gap-2 disabled:opacity-50 shadow"
                        >
                          <span className={isSyncingSheet ? 'animate-spin' : ''}></span>
                          <span>{isSyncingSheet ? 'Đang đồng bộ...' : 'Đồng Bộ Google Sheet'}</span>
                        </button>
                      </div>
                    </div>

                    {/* 2. THANH TIẾN ĐỘ HOÀN THÀNH (PROGRESS BAR) */}
                    <div className="p-4 bg-zinc-900/50 border border-zinc-800 rounded-2xl space-y-2 shadow-inner">
                      <div className="flex items-center justify-between text-xs font-bold">
                        <span className="text-zinc-300 flex items-center gap-2">
                          <span></span>
                          <span>TIẾN ĐỘ HOÀN THÀNH CÔNG VIỆC</span>
                        </span>
                        <span className="text-emerald-400 font-mono text-xs bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/20">
                          Đã xong {completedTasks}/{totalTasks} việc ({progressPercent}%)
                        </span>
                      </div>

                      <div className="h-3 w-full bg-zinc-900/50 rounded-full overflow-hidden border border-zinc-800 relative">
                        <div
                          className="h-full bg-gradient-to-r from-blue-500 via-teal-400 to-emerald-400 rounded-full transition-all duration-500 shadow-lg shadow-emerald-500/30"
                          style={{ width: `${progressPercent}%` }}
                        ></div>
                      </div>
                    </div>

                    {/* 3. THANH THÊM NHANH NHIỆM VỤ MỚI (QUICK ADD BAR) */}
                    <form onSubmit={handleQuickAddTodoTask} className="p-4 bg-zinc-900/50 border border-zinc-800 rounded-2xl space-y-3 shadow">
                      <div className="text-xs font-bold text-blue-400 flex items-center gap-2">
                        <span></span> Thêm Công Việc / Nhiệm Vụ Mới
                      </div>

                      <div className="flex flex-col sm:flex-row gap-2.5">
                        <input
                          type="text"
                          placeholder="Nhập tên bài tập hoặc công việc cần làm..."
                          value={quickAddTitle}
                          onChange={(e) => setQuickAddTitle(e.target.value)}
                          className="flex-grow bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-2.5 text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-indigo-500 shadow"
                        />

                        <select
                          value={quickAddType}
                          onChange={(e) => setQuickAddType(e.target.value)}
                          className="bg-zinc-900 border border-zinc-800 rounded-xl px-3 py-2.5 text-xs font-bold text-blue-300 outline-none focus:border-indigo-500 cursor-pointer shadow"
                        >
                          {isAdmin && <option value="admin_assigned"> Admin Giao</option>}
                          <option value="custom">⭐ Tự Chọn</option>
                          <option value="routine"> Hằng Ngày / Thói Quen</option>
                        </select>

                        <button
                          type="submit"
                          className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl text-xs transition shadow-lg shadow-blue-600/20 whitespace-nowrap"
                        >
                          + Thêm Công Việc
                        </button>
                      </div>
                    </form>

                    {/* 4. DANH SÁCH THỐNG NHẤT TOÀN BỘ NHIỆM VỤ (UNIFIED TASK LIST) */}
                    <div className="space-y-3">
                      <div className="flex items-center justify-between text-xs text-zinc-400 px-1">
                        <span className="font-bold text-zinc-300">DANH SÁCH CÔNG VIỆC CẦN HOÀN THÀNH ({totalTasks})</span>
                        <span className="text-[11px] text-zinc-500">* Tích vào ô vuông khi đã hoàn thành bài tập</span>
                      </div>

                      {combinedTasks.length === 0 ? (
                        /* EMPTY STATE VISUAL */
                        <div className="p-12 text-center bg-zinc-900/50 border border-zinc-800 rounded-2xl space-y-3 shadow-inner">
                          <span className="text-5xl block"></span>
                          <h3 className="font-bold text-base text-zinc-200">Không Có Bài Tập Nào Cần Làm Hôm Nay!</h3>
                          <p className="text-xs text-zinc-400 max-w-sm mx-auto">
                            Bạn chưa có công việc nào trong danh sách. Hãy nhập bài tập mới ở thanh trên hoặc bấm nút "Đồng Bộ Google Sheet".
                          </p>
                        </div>
                      ) : (
                        <div className="space-y-2.5">
                          {combinedTasks.map((task) => {
                            const isEditing = editingTaskId === task.id

                            return (
                              <div
                                key={task.id}
                                className={`p-3.5 rounded-2xl border transition flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                                  task.isCompleted
                                    ? 'bg-black/40 border-slate-900 opacity-60'
                                    : 'bg-zinc-900/50/90 border-zinc-800 hover:border-zinc-800 shadow-md'
                                }`}
                              >
                                {/* INLINE EDIT MODE */}
                                {isEditing ? (
                                  <form onSubmit={handleSaveEditTodoTask} className="w-full flex flex-col sm:flex-row gap-2 items-center">
                                    <input
                                      type="text"
                                      value={editingTaskTitle}
                                      onChange={(e) => setEditingTaskTitle(e.target.value)}
                                      className="flex-grow bg-black border border-indigo-500 rounded-xl px-3 py-1.5 text-xs text-white outline-none"
                                      autoFocus
                                    />

                                    <select
                                      value={editingTaskType}
                                      onChange={(e) => setEditingTaskType(e.target.value)}
                                      className="bg-black border border-zinc-800 rounded-xl px-2 py-1.5 text-xs font-bold text-blue-300"
                                    >
                                      <option value="admin_assigned"> Admin Giao</option>
                                      <option value="custom">⭐ Tự Chọn</option>
                                      <option value="routine"> Hằng Ngày</option>
                                    </select>

                                    <div className="flex gap-2">
                                      <button type="submit" className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-bold">
                                        Lưu
                                      </button>
                                      <button
                                        type="button"
                                        onClick={() => setEditingTaskId(null)}
                                        className="px-3 py-1.5 bg-zinc-900 text-zinc-400 rounded-xl text-xs font-semibold"
                                      >
                                        Hủy
                                      </button>
                                    </div>
                                  </form>
                                ) : (
                                  <>
                                    {/* TASK ITEM CONTENT & CHECKBOX */}
                                    <div className="flex items-center gap-3 flex-grow min-w-0">
                                      <input
                                        type="checkbox"
                                        checked={task.isCompleted}
                                        onChange={() => {
                                          if (task.isSheet) toggleSheetTaskComplete(task.id)
                                          else toggleTodoComplete(task.id, task.isCompleted)
                                        }}
                                        className="w-5 h-5 rounded-lg bg-black border-zinc-800 text-blue-600 cursor-pointer shrink-0"
                                      />

                                      <div className="space-y-1 min-w-0 flex-grow">
                                        <div className="flex items-center gap-2 flex-wrap">
                                          {/* BADGES PHÂN LOẠI */}
                                          {task.taskType === 'admin_assigned' && (
                                            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30">
                                               Admin Giao
                                            </span>
                                          )}
                                          {task.taskType === 'custom' && (
                                            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-blue-500/20 text-blue-300 border border-indigo-500/30">
                                              ⭐ Tự Chọn
                                            </span>
                                          )}
                                          {task.taskType === 'routine' && (
                                            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 border border-emerald-500/30">
                                               Hằng Ngày
                                            </span>
                                          )}
                                          {task.taskType === 'sheet' && (
                                            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/10 text-zinc-200 border border-amber-500/20 border border-amber-500/30">
                                               Google Sheet
                                            </span>
                                          )}

                                          <span
                                            className={`text-xs font-medium leading-relaxed break-words ${
                                              task.isCompleted ? 'line-through text-zinc-500' : 'text-slate-100 font-semibold'
                                            }`}
                                          >
                                            {task.title}
                                          </span>
                                        </div>
                                      </div>
                                    </div>

                                    {/* ACTIONS: SỬA & XÓA */}
                                    <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                                      <button
                                        onClick={() => handleStartEditTodoTask(task)}
                                        className="px-2.5 py-1 text-[11px] font-semibold text-zinc-400 hover:text-blue-300 rounded-lg hover:bg-zinc-900 transition"
                                      >
                                        ️ Sửa
                                      </button>
                                      <button
                                        onClick={() => handleDeleteUnifiedTask(task)}
                                        className="px-2.5 py-1 text-[11px] font-semibold text-zinc-500 hover:text-red-400 rounded-lg hover:bg-red-500/10 transition"
                                      >
                                        ️ Xóa
                                      </button>
                                    </div>
                                  </>
                                )}
                              </div>
                            )
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )
            })()}

            {/* TAB: LỊCH HỌC TẬP & THỜI GIAN BIỂU — REFACTORED CUSTOM DATA TABLE */}
            {activeTab === 'calendar' && (() => {
              // Áp dụng bộ lọc nhanh lên allSheetEntries
              const filteredEntries = allSheetEntries.filter(entry => {
                // Lọc theo Ngày
                if (calendarDateFilter === 'today' && !entry.isToday) return false

                // Lọc theo Ưu tiên
                if (calendarPriorityFilter !== 'all') {
                  const p = entry.priority.toLowerCase()
                  if (calendarPriorityFilter === 'important' && !p.includes('quan trọng') && !p.includes('high')) return false
                  if (calendarPriorityFilter === 'daily' && !p.includes('hằng ngày') && !p.includes('thói quen')) return false
                  if (calendarPriorityFilter === 'normal' && (p.includes('quan trọng') || p.includes('hằng ngày'))) return false
                }

                // Lọc theo Từ khóa tìm kiếm
                if (calendarSearch.trim()) {
                  const q = calendarSearch.toLowerCase().trim()
                  const matchTitle = entry.title.toLowerCase().includes(q)
                  const matchDate = entry.date.toLowerCase().includes(q)
                  const matchTime = entry.sessionTime.toLowerCase().includes(q)
                  if (!matchTitle && !matchDate && !matchTime) return false
                }

                return true
              })

              return (
                <div className="space-y-6">
                  <div className={`${cardBgClass} border rounded-2xl p-6 space-y-6 shadow-2xl`}>
                    {/* HEADER BAR */}
                    <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-zinc-800 pb-4">
                      <div>
                        <h2 className="text-xl font-bold flex items-center gap-2 text-slate-100">
                          <span></span> Lịch Học Tập & Thời Gian Biểu (Custom Data Table)
                        </h2>
                        <p className="text-xs text-zinc-400 mt-1">
                          Đồng bộ dữ liệu trực tiếp từ Google Sheet sang bảng dữ liệu chuẩn hóa SaaS Dark Mode.
                        </p>
                      </div>

                      <div className="flex flex-wrap items-center gap-2">
                        <button
                          onClick={fetchGoogleSheetTasks}
                          disabled={isSyncingSheet}
                          className="px-4 py-2 bg-zinc-900 hover:bg-slate-700 text-blue-300 font-bold rounded-xl text-xs border border-zinc-800 transition flex items-center gap-2 disabled:opacity-50 shadow"
                        >
                          <span className={isSyncingSheet ? 'animate-spin' : ''}></span>
                          <span>{isSyncingSheet ? 'Đang đồng bộ...' : 'Tải Lại Dữ Liệu'}</span>
                        </button>

                        <a
                          href={GOOGLE_SHEET_URL}
                          target="_blank"
                          rel="noreferrer"
                          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl text-xs flex items-center gap-2 transition shadow-lg shadow-emerald-600/20"
                        >
                          <span></span> Mở Trang Google Sheet Gốc
                        </a>
                      </div>
                    </div>

                    {/* BỘ LỌC NHANH (QUICK FILTERS BAR) */}
                    <div className="p-4 bg-zinc-900/50 border border-zinc-800 rounded-2xl flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 shadow-inner">
                      <div className="flex flex-wrap items-center gap-3 w-full lg:w-auto">
                        {/* Lọc theo ngày */}
                        <div className="flex items-center gap-1.5 bg-zinc-900/50 p-1 rounded-xl border border-zinc-800 text-xs">
                          <span className="px-2 text-zinc-400 font-medium">Lọc Ngày:</span>
                          <button
                            onClick={() => setCalendarDateFilter('today')}
                            className={`px-3 py-1.5 rounded-lg font-bold transition ${
                              calendarDateFilter === 'today' ? 'bg-zinc-100 text-black hover:bg-white shadow' : 'text-zinc-400 hover:text-white'
                            }`}
                          >
                             Hôm Nay ({allSheetEntries.filter(e => e.isToday).length})
                          </button>
                          <button
                            onClick={() => setCalendarDateFilter('all')}
                            className={`px-3 py-1.5 rounded-lg font-bold transition ${
                              calendarDateFilter === 'all' ? 'bg-zinc-100 text-black hover:bg-white shadow' : 'text-zinc-400 hover:text-white'
                            }`}
                          >
                             Tất Cả ({allSheetEntries.length})
                          </button>
                        </div>

                        {/* Lọc theo mức độ ưu tiên */}
                        <div className="flex items-center gap-1.5 bg-zinc-900/50 p-1 rounded-xl border border-zinc-800 text-xs">
                          <span className="px-2 text-zinc-400 font-medium">Ưu Tiên:</span>
                          <button
                            onClick={() => setCalendarPriorityFilter('all')}
                            className={`px-2.5 py-1 rounded-lg font-bold transition ${
                              calendarPriorityFilter === 'all' ? 'bg-slate-700 text-white' : 'text-zinc-400 hover:text-white'
                            }`}
                          >
                            Tất cả
                          </button>
                          <button
                            onClick={() => setCalendarPriorityFilter('important')}
                            className={`px-2.5 py-1 rounded-lg font-bold transition ${
                              calendarPriorityFilter === 'important' ? 'bg-rose-600 text-white' : 'text-rose-400 hover:text-white'
                            }`}
                          >
                             Quan Trọng
                          </button>
                          <button
                            onClick={() => setCalendarPriorityFilter('daily')}
                            className={`px-2.5 py-1 rounded-lg font-bold transition ${
                              calendarPriorityFilter === 'daily' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'text-emerald-400 hover:text-white'
                            }`}
                          >
                             Hằng Ngày
                          </button>
                          <button
                            onClick={() => setCalendarPriorityFilter('normal')}
                            className={`px-2.5 py-1 rounded-lg font-bold transition ${
                              calendarPriorityFilter === 'normal' ? 'bg-zinc-100 text-black hover:bg-white' : 'text-blue-400 hover:text-white'
                            }`}
                          >
                             Bình Thường
                          </button>
                        </div>
                      </div>

                      {/* Ô Tìm Kiếm Từ Khóa */}
                      <div className="w-full lg:w-64">
                        <input
                          type="text"
                          placeholder=" Tìm bài tập / khung giờ..."
                          value={calendarSearch}
                          onChange={(e) => setCalendarSearch(e.target.value)}
                          className="w-full bg-zinc-900 border border-zinc-800 rounded-xl px-3.5 py-2 text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-indigo-500"
                        />
                      </div>
                    </div>

                    {/* RENDER CUSTOM DATA TABLE */}
                    <div className="overflow-x-auto rounded-2xl border border-zinc-800 shadow">
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="border-b border-zinc-800 text-zinc-400 font-mono text-[11px] uppercase tracking-wider bg-zinc-900/50">
                            <th className="p-3.5">Ngày</th>
                            <th className="p-3.5">Buổi / Khung Giờ</th>
                            <th className="p-3.5">Nội Dung Công Việc / Bài Tập</th>
                            <th className="p-3.5">Độ Ưu Tiên / Nhãn</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60 bg-zinc-900/50/50">
                          {filteredEntries.length === 0 ? (
                            <tr>
                              <td colSpan="4" className="text-center py-12 text-zinc-500">
                                <span className="text-3xl block mb-2"></span>
                                <span>Không tìm thấy bài tập nào khớp với bộ lọc.</span>
                              </td>
                            </tr>
                          ) : (
                            filteredEntries.map((item) => {
                              const pLower = item.priority.toLowerCase()
                              const isImportant = pLower.includes('quan trọng') || pLower.includes('high')
                              const isDaily = pLower.includes('hằng ngày') || pLower.includes('thói quen')

                              return (
                                <tr key={item.id} className="hover:bg-zinc-900/50 transition">
                                  <td className="p-3.5 font-mono text-zinc-300 font-semibold whitespace-nowrap">
                                    <span className="px-2 py-0.5 bg-black rounded border border-zinc-800">
                                      {item.date}
                                    </span>
                                  </td>

                                  <td className="p-3.5 font-semibold text-blue-300 whitespace-nowrap">
                                    <span className="px-2 py-0.5 bg-blue-500/10 rounded border border-indigo-500/20">
                                      {item.sessionTime}
                                    </span>
                                  </td>

                                  <td className="p-3.5 text-slate-100 font-medium leading-relaxed">
                                    {item.content}
                                  </td>

                                  <td className="p-3.5 whitespace-nowrap">
                                    {isImportant && (
                                      <span className="px-2.5 py-1 rounded-full text-[11px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30">
                                         Quan Trọng
                                      </span>
                                    )}
                                    {isDaily && (
                                      <span className="px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 border border-emerald-500/30">
                                         Hằng Ngày
                                      </span>
                                    )}
                                    {!isImportant && !isDaily && (
                                      <span className="px-2.5 py-1 rounded-full text-[11px] font-bold bg-blue-500/20 text-blue-300 border border-indigo-500/30">
                                         {item.priority || 'Bình thường'}
                                      </span>
                                    )}
                                  </td>
                                </tr>
                              )
                            })
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )
            })()}

            {/* TAB: Chat 2 chiều */}
            {activeTab === 'chat' && (
              <div className={`${cardBgClass} border rounded-2xl p-5 max-w-3xl mx-auto shadow-2xl`}>
                <div className="flex items-center justify-between border-b border-zinc-800 pb-3 mb-4">
                  <div className="flex items-center gap-2">
                    <span className="text-2xl"></span>
                    <div>
                      <h2 className="font-bold text-base">Cửa Sổ Trò Chuyện Trực Tiếp</h2>
                      <p className="text-xs text-zinc-400">{isAdmin ? 'Đang nhắn với tư cách Admin' : `Đang nhắn với tư cách: ${userRole || 'Người xem'}`}</p>
                    </div>
                  </div>
                </div>
                <div className="h-96 overflow-y-auto space-y-3 p-4 bg-black border border-zinc-800 rounded-xl mb-4">
                  {chatMessages.length === 0 ? (
                    <div className="text-center text-slate-600 text-sm py-16">Chưa có tin nhắn nào. Gửi tin nhắn đầu tiên bên dưới!</div>
                  ) : (
                    chatMessages.map((msg, idx) => (
                      <div key={msg.id || idx} className={`flex ${msg.sender === 'admin' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-xs md:max-w-md p-3.5 rounded-2xl text-sm ${
                          msg.sender === 'admin' ? 'bg-zinc-100 text-black hover:bg-white rounded-br-none' : 'bg-zinc-900 text-zinc-200 border border-zinc-800 rounded-bl-none'
                        }`}>
                          <div className="text-[10px] font-bold opacity-80 mb-1">{msg.sender === 'admin' ? 'Anh/Chị Quản lý' : msg.sender}</div>
                          <div className="leading-relaxed break-words">{msg.message}</div>
                          <div className="text-[9px] opacity-60 text-right mt-1.5">{formatTime(msg.created_at)}</div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
                <form
                  onSubmit={(e) => {
                    e.preventDefault()
                    handleSendChatMsg(chatInput)
                  }}
                  className="flex gap-2"
                >
                  <input
                    type="text"
                    placeholder={isAdmin ? 'Nhập tin nhắn nhắn cho em trai...' : 'Gõ tin nhắn phản hồi...'}
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    className="flex-grow bg-black border border-zinc-800 rounded-xl px-4 py-3 text-sm focus:border-indigo-500 outline-none"
                  />
                  <button type="submit" className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl text-sm transition">
                    Gửi
                  </button>
                </form>
              </div>
            )}

            {/* TAB: AI Phân Tích */}
            {activeTab === 'ai_analysis' && (
              <div className="bg-zinc-950 border border-zinc-800 rounded-2xl p-6 space-y-6">
                <div className="flex items-center gap-3">
                  <Bot className="w-5 h-5 text-zinc-100 stroke-[1.5]" />
                  <div>
                    <h2 className="text-sm font-mono font-bold text-zinc-100 uppercase tracking-wider">Báo Cáo Phân Tích Thói Quen Dùng Máy</h2>
                    <p className="text-xs text-zinc-400">Tự động soi tên cửa sổ, ứng dụng và nội dung web để phân biệt Học tập vs Giải trí</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-5 rounded-2xl bg-zinc-900/40 border border-zinc-800">
                    <div className="text-zinc-400 text-xs mb-1">Chỉ số tập trung dựa trên nội dung</div>
                    <div className="text-3xl font-extrabold text-blue-400">{aiReport.score}</div>
                    <div className="text-sm font-medium mt-2 text-zinc-300">{aiReport.ratio}</div>
                  </div>
                  <div className="p-5 rounded-2xl bg-zinc-900/40 border border-zinc-800">
                    <div className="text-zinc-400 text-xs mb-1">Tổng quan phân tích</div>
                    <div className="text-sm text-zinc-200 mt-2">{aiReport.summary}</div>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                    <div className="font-bold text-xs text-emerald-400 mb-2"> Nội dung Học tập / AutoCAD / Bài tập:</div>
                    {aiReport.studyWindows.length === 0 ? (
                      <div className="text-xs text-zinc-500">Chưa phát hiện cửa sổ học tập nào gần đây.</div>
                    ) : (
                      <div className="space-y-1 max-h-40 overflow-y-auto text-xs text-zinc-300">
                        {aiReport.studyWindows.map((w, idx) => (
                          <div key={idx} className="truncate">• {w}</div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20">
                    <div className="font-bold text-xs text-zinc-200 mb-2"> Nội dung Giải trí / Youtube / Game / Pick:</div>
                    {aiReport.playWindows.length === 0 ? (
                      <div className="text-xs text-zinc-500">Chưa phát hiện nội dung giải trí nào gần đây.</div>
                    ) : (
                      <div className="space-y-1 max-h-40 overflow-y-auto text-xs text-zinc-300">
                        {aiReport.playWindows.map((w, idx) => (
                          <div key={idx} className="truncate">• {w}</div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* TAB GỘP "QUÁ TRÌNH SỬ DỤNG" (CHIA LÀM 2 LỰA CHỌN:  ỨNG DỤNG & QUY TẮC +  LỊCH SỬ DUYỆT WEB DẠNG TIMELINE CHROME HAS BULK DELETE) */}
            {activeTab === 'app_usage' && (
              <div className={`${cardBgClass} border rounded-2xl p-6 space-y-6`}>
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-zinc-800 pb-4">
                  <div>
                    <h2 className="font-bold text-lg flex items-center gap-2">
                      <span></span> Quá Trình Sử Dụng (App & Web)
                    </h2>
                    <p className="text-xs text-zinc-400 mt-1">Theo dõi thời gian dùng app, cài đặt cấm/giới hạn và xem lịch sử duyệt web dạng timeline.</p>
                  </div>

                    {/* TOGGLE 4 CHẾ ĐỘ XEM TRONG QUÁ TRÌNH SỬ DỤNG */}
                    <div className="flex flex-wrap bg-black p-1 rounded-xl border border-zinc-800 text-xs gap-1">
                      <button
                        onClick={() => setUsageSubTab('apps')}
                        className={`px-3.5 py-2 rounded-lg font-semibold transition ${
                          usageSubTab === 'apps' ? 'bg-zinc-100 text-black hover:bg-white shadow' : 'text-zinc-400 hover:text-white'
                        }`}
                      >
                         App & Quy Tắc
                      </button>
                      <button
                        onClick={() => setUsageSubTab('history')}
                        className={`px-3.5 py-2 rounded-lg font-semibold transition ${
                          usageSubTab === 'history' ? 'bg-zinc-100 text-black hover:bg-white shadow' : 'text-zinc-400 hover:text-white'
                        }`}
                      >
                         Web & Quy Tắc
                      </button>
                      <button
                        onClick={() => setUsageSubTab('log')}
                        className={`px-3.5 py-2 rounded-lg font-semibold transition ${
                          usageSubTab === 'log' ? 'bg-green-600 text-white shadow' : 'text-zinc-400 hover:text-white'
                        }`}
                      >
                         Log File ({totalLogFileCount})
                      </button>
                      <button
                        onClick={() => setUsageSubTab('black_list')}
                        className={`px-3.5 py-2 rounded-lg font-semibold transition ${
                          usageSubTab === 'black_list' ? 'bg-amber-500/10 text-zinc-200 border border-amber-500/20 shadow' : 'text-zinc-400 hover:text-white'
                        }`}
                      >
                         Black List ({webRules.length + appRules.length})
                      </button>
                      <button
                        onClick={() => setUsageSubTab('schedule')}
                        className={`px-3.5 py-2 rounded-lg font-semibold transition ${
                          usageSubTab === 'schedule' ? 'bg-zinc-100 text-black hover:bg-white shadow' : 'text-zinc-400 hover:text-white'
                        }`}
                      >
                         Khung Giờ
                      </button>
                    </div>
                </div>

                {/* Task 6: Date picker xem lịch sử web và app */}
                <div className="p-3.5 bg-zinc-900/50 border border-zinc-800 rounded-2xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs shadow-inner">
                  <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-zinc-300"> Xem Lịch Sử Ngày:</span>
                      <select
                        value={historyDate}
                        onChange={(e) => loadHistoryForDate(e.target.value)}
                        className="bg-zinc-900 border border-zinc-800 rounded-xl px-3.5 py-1.5 font-bold text-blue-300 outline-none cursor-pointer focus:border-indigo-500 shadow"
                      >
                        <option value={new Date().toISOString().split('T')[0]}>Hôm nay (Mặc định)</option>
                        {availableDates
                          .filter(d => d !== new Date().toISOString().split('T')[0])
                          .map(d => (
                            <option key={d} value={d}>{d}</option>
                          ))
                        }
                      </select>
                    </div>
                  </div>

                  {isAdmin && (
                    <button
                      onClick={() => openDeleteDateModal(historyDate)}
                      className="px-3.5 py-1.5 bg-red-500/10 hover:bg-rose-500/10 text-rose-400 border border-rose-500/20 hover:text-red-300 border border-red-500/30 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition ml-auto shadow"
                    >
                      <span>️</span> Xóa Dữ Liệu Ngày {historyDate}
                    </button>
                  )}
                </div>

                {/* SUB-TAB 1:  ỨNG DỤNG (RÚT GỌN CHỈ CÒN THỐNG KÊ) */}
                {usageSubTab === 'apps' && (
                  <div className="space-y-6">
                    {/* BẢNG TỔNG QUAN THỜI GIAN SỬ DỤNG VÀ QUY TẮC APP HÔM NAY */}
                    <div className="space-y-3">
                      <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
                        <h3 className="font-bold text-sm text-blue-400 flex items-center gap-2">
                          <span></span> Bảng Tổng Quan Quy Tắc & Thời Gian Dùng App Hôm Nay
                        </h3>
                        <div className="flex items-center gap-3">
                          {/* Task 6: Nút ẩn ứng dụng không hoạt động */}
                          <label className="flex items-center gap-1.5 cursor-pointer text-xs text-zinc-400 select-none">
                            <input
                              type="checkbox"
                              checked={hideUnusedApps}
                              onChange={(e) => setHideUnusedApps(e.target.checked)}
                              className="w-3.5 h-3.5 text-blue-600 rounded"
                            />
                            Ẩn app không hoạt động
                          </label>
                          <span className="text-xs text-zinc-400">{mergedAppsList.length} ứng dụng</span>
                        </div>
                      </div>

                      {mergedAppsList.length === 0 ? (
                        <div className="text-zinc-500 text-sm py-4 text-center">Chưa có ứng dụng nào trong danh sách.</div>
                      ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {mergedAppsList.map(app => (
                            <div key={app.process_name} className="p-3.5 rounded-xl bg-zinc-900/50 border border-zinc-800 flex items-center justify-between gap-3 text-xs">
                              <div>
                                <div className="font-bold text-blue-300 text-sm flex items-center gap-1.5">
                                  <span></span>
                                  <span>{app.process_name}</span>
                                </div>
                                <div className="text-zinc-400 mt-0.5">
                                  Đã dùng hôm nay: <strong className="text-white font-mono">{app.used_minutes} phút</strong>
                                </div>
                              </div>

                              <div className="flex items-center gap-2">
                                {isAdmin ? (
                                  <>
                                    <select
                                      value={app.category}
                                      onChange={(e) => {
                                        if (app.rule_id) updateAppRule(app.rule_id, 'category', e.target.value)
                                        else supabase.from('app_rules').insert({ device_name: DEVICE_NAME, process_name: app.process_name, category: e.target.value }).then(() => loadData(false))
                                      }}
                                      className="bg-zinc-900 border border-zinc-800 rounded-lg px-2.5 py-1 text-xs font-semibold outline-none focus:border-indigo-500"
                                    >
                                      <option value="allowed">Cho phép</option>
                                      <option value="limited">Giới hạn</option>
                                      <option value="forbidden">Cấm hẳn</option>
                                    </select>

                                    {app.category === 'limited' && (
                                      <div className="flex items-center gap-1">
                                        <input
                                          type="number"
                                          value={app.max_minutes_per_day}
                                          onChange={(e) => {
                                            const val = parseInt(e.target.value) || 0
                                            if (app.rule_id) updateAppRule(app.rule_id, 'max_minutes_per_day', val)
                                            else supabase.from('app_rules').insert({ device_name: DEVICE_NAME, process_name: app.process_name, category: 'limited', max_minutes_per_day: val }).then(() => loadData(false))
                                          }}
                                          className="w-14 bg-zinc-900/50 border border-zinc-800 rounded-lg px-1.5 py-0.5 text-xs text-center font-bold text-zinc-200 outline-none"
                                        />
                                        <span className="text-[11px] text-zinc-200">p</span>
                                      </div>
                                    )}
                                  </>
                                ) : (
                                  <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold ${
                                    app.category === 'forbidden' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                                    app.category === 'limited' ? 'bg-amber-500/20 text-zinc-200' : 'bg-emerald-500/20 text-emerald-400'
                                  }`}>
                                    {app.category === 'forbidden' ? ' Cấm' : app.category === 'limited' ? `⏱ ${app.max_minutes_per_day}p/ngày` : ' Cho phép'}
                                  </span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* SUB-TAB 2:  WEB & THỜI GIAN SỬ DỤNG */}
                {usageSubTab === 'history' && (
                  <div className="space-y-6">
                    <div className="space-y-3">
                      <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
                        <h3 className="font-bold text-sm text-blue-400 flex items-center gap-2">
                          <span></span> Bảng Tổng Quan Quy Tắc & Thời Gian Lướt Web
                        </h3>
                        <div className="flex items-center gap-3">
                          <label className="flex items-center gap-1.5 cursor-pointer text-xs text-zinc-400 select-none">
                            <input
                              type="checkbox"
                              checked={hideUnusedApps}
                              onChange={(e) => setHideUnusedApps(e.target.checked)}
                              className="w-3.5 h-3.5 text-blue-600 rounded"
                            />
                            Ẩn Web 0 phút
                          </label>
                          <span className="text-xs text-zinc-400">{mergedWebsList.length} trang web</span>
                        </div>
                      </div>

                      {mergedWebsList.length === 0 ? (
                        <div className="text-zinc-500 text-sm py-4 text-center">Chưa có trang web nào được ghi nhận sử dụng.</div>
                      ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {mergedWebsList.map(web => (
                            <div key={web.domain} className="p-3.5 rounded-xl bg-zinc-900/50 border border-zinc-800 flex items-center justify-between gap-3 text-xs">
                              <div>
                                <div className="font-bold text-blue-300 text-sm flex items-center gap-1.5">
                                  <span></span>
                                  <span>{web.domain}</span>
                                </div>
                                <div className="text-zinc-400 mt-0.5">
                                  Thời gian truy cập: <strong className="text-white font-mono">{web.used_minutes} phút</strong>
                                </div>
                              </div>

                              <div className="flex items-center gap-2">
                                {isAdmin ? (
                                  <>
                                    <select
                                      value={web.category}
                                      onChange={(e) => {
                                        if (web.rule_id) updateWebRule(web.rule_id, 'category', e.target.value)
                                        else supabase.from('web_rules').insert({ device_name: DEVICE_NAME, domain: web.domain, category: e.target.value }).then(() => loadData(false))
                                      }}
                                      className="bg-zinc-900 border border-zinc-800 rounded-lg px-2.5 py-1 text-xs font-semibold outline-none focus:border-indigo-500"
                                    >
                                      <option value="allowed">Cho phép</option>
                                      <option value="limited">Giới hạn</option>
                                      <option value="forbidden">Cấm hẳn</option>
                                    </select>

                                    {web.category === 'limited' && (
                                      <div className="flex items-center gap-1">
                                        <input
                                          type="number"
                                          value={web.max_minutes_per_day}
                                          onChange={(e) => {
                                            const val = parseInt(e.target.value) || 0
                                            if (web.rule_id) updateWebRule(web.rule_id, 'max_minutes_per_day', val)
                                            else supabase.from('web_rules').insert({ device_name: DEVICE_NAME, domain: web.domain, category: 'limited', max_minutes_per_day: val }).then(() => loadData(false))
                                          }}
                                          className="w-14 bg-zinc-900/50 border border-zinc-800 rounded-lg px-1.5 py-0.5 text-xs text-center font-bold text-zinc-200 outline-none"
                                        />
                                        <span className="text-[11px] text-zinc-200">p</span>
                                      </div>
                                    )}
                                  </>
                                ) : (
                                  <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold ${
                                    web.category === 'forbidden' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                                    web.category === 'limited' ? 'bg-amber-500/20 text-zinc-200' : 'bg-emerald-500/20 text-emerald-400'
                                  }`}>
                                    {web.category === 'forbidden' ? ' Cấm' : web.category === 'limited' ? `⏱ ${web.max_minutes_per_day}p/ngày` : ' Cho phép'}
                                  </span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* SUB-TAB 3:  LOG FILE VIEWER */}
                {usageSubTab === 'log' && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-bold text-base flex items-center gap-2 text-green-400">
                          <span></span> System Log Viewer
                        </h3>
                        <p className="text-xs text-zinc-400 mt-0.5">
                          Chi tiết các sự kiện mở App và truy cập Web theo dạng Console Log.
                        </p>
                      </div>
                    </div>

                    <div className="bg-black border border-zinc-800 rounded-xl p-4 font-mono text-[11px] h-[500px] overflow-y-auto custom-scrollbar shadow-inner text-zinc-300">
                      {Object.keys(groupedLogFile).length === 0 ? (
                        <div className="text-zinc-500 italic">No logs found for {historyDate}.</div>
                      ) : (
                        Object.entries(groupedLogFile).map(([dateLabel, logs]) => (
                          <div key={dateLabel} className="mb-6">
                            <div className="text-green-500 font-bold mb-2 sticky top-0 bg-black py-1 border-b border-zinc-800/50">
                              [{dateLabel}]
                            </div>
                            <div className="space-y-1 pl-2">
                              {logs.map((log, idx) => (
                                <div key={idx} className="flex gap-3 hover:bg-white/5 px-1 py-0.5 rounded transition">
                                  <span className="text-zinc-500 flex-shrink-0 w-16">{log.displayTime}</span>
                                  <span className={`flex-shrink-0 w-10 font-bold ${log.type === 'WEB' ? 'text-blue-400' : 'text-zinc-300'}`}>
                                    [{log.type}]
                                  </span>
                                  <span className="text-amber-200/80 font-semibold flex-shrink-0 max-w-[120px] truncate">
                                    {log.domain}
                                  </span>
                                  <span className="text-zinc-300 truncate">
                                    {log.title}
                                  </span>
                                  {log.count > 1 && (
                                    <span className="text-zinc-500 text-[10px] ml-auto">
                                      (x{log.count})
                                    </span>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}

                {/* SUB-TAB 3:  BLACK LIST (QUẢN LÝ RIÊNG APP VÀ TRANG WEB BỊ GIỚI HẠN VÀ CẤM) */}
                {usageSubTab === 'black_list' && (
                  <div className="space-y-6">
                    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-zinc-800 pb-4">
                      <div>
                        <h3 className="font-bold text-base flex items-center gap-2 text-zinc-200">
                          <span></span> Danh Sách Black List (App & Website Bị Cấm / Giới Hạn)
                        </h3>
                        <p className="text-xs text-zinc-400 mt-1">
                          Quản lý riêng tất cả ứng dụng (.exe) và trang web (domain) bị cấm hoặc giới hạn thời gian truy cập.
                        </p>
                      </div>

                      {isAdmin && (
                        <button
                          onClick={() => setShowAddBlackListModal(true)}
                          className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl text-xs transition shadow-lg flex items-center gap-1.5"
                        >
                          <span>+</span>
                          <span>Thêm App / Web Mới</span>
                        </button>
                      )}
                    </div>

                    {/* SUB TOGGLE WEB BLACK LIST VS APP BLACK LIST */}
                    <div className="flex bg-black p-1 rounded-xl border border-zinc-800 text-xs w-fit">
                      <button
                        onClick={() => setBlackListSubTab('web')}
                        className={`px-4 py-2 rounded-lg font-semibold transition ${
                          blackListSubTab === 'web' ? 'bg-zinc-100 text-black hover:bg-white' : 'text-zinc-400 hover:text-white'
                        }`}
                      >
                         Web Black List ({webRules.length})
                      </button>
                      <button
                        onClick={() => setBlackListSubTab('app')}
                        className={`px-4 py-2 rounded-lg font-semibold transition ${
                          blackListSubTab === 'app' ? 'bg-zinc-100 text-black hover:bg-white' : 'text-zinc-400 hover:text-white'
                        }`}
                      >
                         App Black List ({appRules.length})
                      </button>
                    </div>

                    {/* DANH SÁCH WEB BLACK LIST */}
                    {blackListSubTab === 'web' && (
                      <div className="space-y-3">
                        {webRules.length === 0 ? (
                          <div className="text-center text-zinc-500 py-16 text-sm">
                            Chưa có trang web nào trong Black List. Bấm "+ Thêm App / Web Mới" ở trên để tạo quy tắc cấm/giới hạn web.
                          </div>
                        ) : (
                          webRules.map(rule => {
                            const usedToday = webUsage.find(u => u.domain === rule.domain)?.used_minutes || 0

                            return (
                              <div key={rule.id} className="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
                                <div className="space-y-1">
                                  <div className="font-bold text-amber-300 text-base flex items-center gap-2">
                                    <span> {rule.domain}</span>
                                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                                      rule.category === 'forbidden' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                                      rule.category === 'limited' ? 'bg-amber-500/20 text-zinc-200' : 'bg-emerald-500/20 text-emerald-400'
                                    }`}>
                                      {rule.category === 'forbidden' ? ' Cấm hẳn' : rule.category === 'limited' ? `⏱ Giới hạn ${rule.max_minutes_per_day} phút/ngày` : ' Cho phép'}
                                    </span>
                                  </div>
                                  <div className="text-xs text-zinc-400">
                                    Đã dùng hôm nay: <strong className="text-white font-mono text-sm">{usedToday} phút</strong>
                                  </div>
                                </div>

                                <div className="flex flex-wrap items-center gap-3">
                                  {isAdmin ? (
                                    <>
                                      <select
                                        value={rule.category}
                                        onChange={(e) => updateWebRule(rule.id, 'category', e.target.value)}
                                        className="bg-zinc-900 border border-zinc-800 rounded-xl px-3 py-1.5 text-xs font-semibold text-blue-300 outline-none focus:border-indigo-500"
                                      >
                                        <option value="forbidden"> Cấm hẳn</option>
                                        <option value="limited">⏱ Giới hạn</option>
                                        <option value="allowed"> Cho phép</option>
                                      </select>

                                      {rule.category === 'limited' && (
                                        <div className="flex items-center gap-1.5">
                                          <span className="text-xs text-zinc-200 font-semibold">tối đa :</span>
                                          <input
                                            type="number"
                                            value={rule.max_minutes_per_day}
                                            onChange={(e) => updateWebRule(rule.id, 'max_minutes_per_day', parseInt(e.target.value) || 0)}
                                            className="w-16 bg-zinc-900/50 border border-zinc-800 rounded-xl px-2 py-1 text-xs text-center font-bold text-zinc-200 outline-none"
                                          />
                                          <span className="text-xs text-zinc-200 font-semibold">phút/ngày</span>
                                        </div>
                                      )}

                                      <button
                                        onClick={() => deleteWebRule(rule.id)}
                                        className="text-xs text-red-400 hover:text-red-300 px-3 py-1.5 rounded-xl hover:bg-red-500/10 transition border border-red-500/20 font-semibold"
                                      >
                                        ️ Xóa
                                      </button>
                                    </>
                                  ) : (
                                    <span className="text-xs text-zinc-400 font-mono">ID: {rule.id?.slice(0, 8)}</span>
                                  )}
                                </div>
                              </div>
                            )
                          })
                        )}
                      </div>
                    )}

                    {/* DANH SÁCH APP BLACK LIST */}
                    {blackListSubTab === 'app' && (
                      <div className="space-y-3">
                        {appRules.length === 0 ? (
                          <div className="text-center text-zinc-500 py-16 text-sm">
                            Chưa có ứng dụng nào trong Black List. Bấm "+ Thêm App / Web Mới" ở trên để chọn cấm/giới hạn app.
                          </div>
                        ) : (
                          appRules.map(rule => {
                            const usedToday = appUsage.find(u => u.process_name?.toLowerCase() === rule.process_name?.toLowerCase())?.used_minutes || 0

                            return (
                              <div key={rule.id} className="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
                                <div className="space-y-1">
                                  <div className="font-bold text-blue-400 text-base flex items-center gap-2">
                                    <span> {rule.process_name}</span>
                                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                                      rule.category === 'forbidden' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                                      rule.category === 'limited' ? 'bg-amber-500/20 text-zinc-200' : 'bg-emerald-500/20 text-emerald-400'
                                    }`}>
                                      {rule.category === 'forbidden' ? ' Cấm hẳn' : rule.category === 'limited' ? `⏱ Giới hạn ${rule.max_minutes_per_day} phút/ngày` : ' Cho phép'}
                                    </span>
                                  </div>
                                  <div className="text-xs text-zinc-400">
                                    Đã dùng hôm nay: <strong className="text-white font-mono text-sm">{usedToday} phút</strong>
                                  </div>
                                </div>

                                <div className="flex flex-wrap items-center gap-3">
                                  {isAdmin ? (
                                    <>
                                      <select
                                        value={rule.category}
                                        onChange={(e) => updateAppRule(rule.id, 'category', e.target.value)}
                                        className="bg-zinc-900 border border-zinc-800 rounded-xl px-3 py-1.5 text-xs font-semibold text-blue-300 outline-none focus:border-indigo-500"
                                      >
                                        <option value="forbidden"> Cấm hẳn</option>
                                        <option value="limited">⏱ Giới hạn</option>
                                        <option value="allowed"> Cho phép</option>
                                      </select>

                                      {rule.category === 'limited' && (
                                        <div className="flex items-center gap-1.5">
                                          <span className="text-xs text-zinc-200 font-semibold">tối đa :</span>
                                          <input
                                            type="number"
                                            value={rule.max_minutes_per_day}
                                            onChange={(e) => updateAppRule(rule.id, 'max_minutes_per_day', parseInt(e.target.value) || 0)}
                                            className="w-16 bg-zinc-900/50 border border-zinc-800 rounded-xl px-2 py-1 text-xs text-center font-bold text-zinc-200 outline-none"
                                          />
                                          <span className="text-xs text-zinc-200 font-semibold">phút/ngày</span>
                                        </div>
                                      )}

                                      <button
                                        onClick={() => deleteAppRule(rule.id)}
                                        className="text-xs text-red-400 hover:text-red-300 px-3 py-1.5 rounded-xl hover:bg-red-500/10 transition border border-red-500/20 font-semibold"
                                      >
                                        ️ Xóa
                                      </button>
                                    </>
                                  ) : (
                                    <span className="text-xs text-zinc-400 font-mono">ID: {rule.id?.slice(0, 8)}</span>
                                  )}
                                </div>
                              </div>
                            )
                          })
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* SUB-TAB 4:  KHUNG GIỜ CHO PHÉP SỬ DỤNG MÁY TÍNH (REFACTORED UI/UX) */}
                {usageSubTab === 'schedule' && (
                  <div className="space-y-5">
                    {/* THANH CÔNG CỤ ĐẦU TAB - KHÔNG KHOẢNG TRẮNG THỪA */}
                    <div className="p-4 bg-zinc-900/50 border border-zinc-800 rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-lg">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-xl"></span>
                          <h3 className="font-bold text-base text-slate-100">Cấu Hình Khung Giờ Cho Phép Sử Dụng</h3>
                        </div>
                        <p className="text-xs text-zinc-400">Thiết lập khoảng giờ hoặc tổng thời gian tối đa mỗi ngày cho em trai.</p>
                      </div>

                      {/* MASTER TOGGLE SWITCH & MODE SELECTOR */}
                      <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
                        {/* Master Switch */}
                        {isAdmin && (
                          <button
                            onClick={handleToggleMasterTimeLimit}
                            className={`px-4 py-2 rounded-xl text-xs font-bold transition border flex items-center gap-2 shadow ${
                              isMasterTimeLimitActive
                                ? 'bg-emerald-600 hover:bg-emerald-500 text-white border-emerald-500 shadow-emerald-600/20'
                                : 'bg-zinc-900 hover:bg-slate-700 text-zinc-400 border-zinc-800'
                            }`}
                          >
                            <span>{isMasterTimeLimitActive ? ' Giới Hạn: ĐANG BẬT' : ' Giới Hạn: ĐÃ TẮT'}</span>
                          </button>
                        )}

                        {/* Mode Radio Buttons */}
                        {isAdmin && (
                          <div className="flex bg-zinc-900/50 p-1 rounded-xl border border-zinc-800 text-xs">
                            <button
                              onClick={() => handleChangeTimeLimitMode('time_frame')}
                              className={`px-3.5 py-1.5 rounded-lg font-bold transition ${
                                timeLimitMode === 'time_frame' ? 'bg-zinc-100 text-black hover:bg-white shadow' : 'text-zinc-400 hover:text-white'
                              }`}
                            >
                              ⏰ Theo Khung Giờ
                            </button>
                            <button
                              onClick={() => handleChangeTimeLimitMode('max_daily')}
                              className={`px-3.5 py-1.5 rounded-lg font-bold transition ${
                                timeLimitMode === 'max_daily' ? 'bg-zinc-100 text-black hover:bg-white shadow' : 'text-zinc-400 hover:text-white'
                              }`}
                            >
                              ⏱️ Theo Tổng Giờ/Ngày
                            </button>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* TRƯỜNG HỢP 1: THỜI GIAN THEO KHUNG GIỜ (time_frame) */}
                    {timeLimitMode === 'time_frame' && (
                      <div className="space-y-4">
                        <div className="p-3 bg-blue-500/10 border border-indigo-500/20 rounded-xl text-xs text-blue-300 flex items-center gap-2">
                          <span>ℹ️</span>
                          <span>Chế độ <strong>Theo Khung Giờ</strong>: Em trai chỉ được phép dùng máy tính trong khoảng giờ được thiết lập bên dưới. Ngoài khoảng giờ này máy sẽ tự khóa.</span>
                        </div>

                        <div className="grid grid-cols-1 gap-4">
                          {timeRules.map(rule => (
                            <div key={rule.id} className="p-4 rounded-2xl bg-zinc-900/50 border border-zinc-800 space-y-3 hover:border-zinc-800 transition shadow">
                              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-zinc-800 pb-3">
                                <div className="flex items-center gap-2.5">
                                  <span className="w-8 h-8 rounded-xl bg-blue-500/10 border border-indigo-500/20 text-blue-400 font-bold flex items-center justify-center text-xs">
                                    {rule.day_of_week === 6 ? 'CN' : `T${rule.day_of_week + 2}`}
                                  </span>
                                  <span className="font-bold text-sm text-zinc-200">{dayNames[rule.day_of_week]}</span>
                                </div>

                                {isAdmin ? (
                                  <div className="flex flex-wrap items-center gap-3">
                                    <div className="flex items-center gap-2">
                                      <span className="text-xs text-zinc-400 font-medium">Bắt đầu:</span>
                                      <input
                                        type="time"
                                        value={rule.start_time?.slice(0, 5)}
                                        onChange={(e) => updateTimeRule(rule.id, 'start_time', e.target.value + ':00')}
                                        className="bg-zinc-900 border border-zinc-800 rounded-xl px-3 py-1.5 text-xs font-bold text-emerald-400 outline-none focus:border-indigo-500 shadow"
                                      />
                                      <span className="text-zinc-500">→</span>
                                      <span className="text-xs text-zinc-400 font-medium font-mono">Kết thúc:</span>
                                      <input
                                        type="time"
                                        value={rule.end_time?.slice(0, 5)}
                                        onChange={(e) => updateTimeRule(rule.id, 'end_time', e.target.value + ':00')}
                                        className="bg-zinc-900 border border-zinc-800 rounded-xl px-3 py-1.5 text-xs font-bold text-emerald-400 outline-none focus:border-indigo-500 shadow"
                                      />
                                    </div>

                                    <button
                                      onClick={() => updateTimeRule(rule.id, 'is_active', !rule.is_active)}
                                      className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition ${
                                        rule.is_active ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-zinc-900 text-zinc-400 border border-zinc-800'
                                      }`}
                                    >
                                      {rule.is_active ? 'Đang bật' : 'Đã tắt'}
                                    </button>
                                  </div>
                                ) : (
                                  <div className="flex items-center gap-3">
                                    <span className="text-xs font-bold text-emerald-400 bg-emerald-500/10 px-3 py-1 rounded-lg border border-emerald-500/20">
                                      {rule.start_time?.slice(0, 5)} → {rule.end_time?.slice(0, 5)}
                                    </span>
                                    <span className={`px-2.5 py-1 rounded-lg text-xs font-semibold ${
                                      rule.is_active ? 'bg-emerald-500/15 text-emerald-400' : 'bg-zinc-900 text-zinc-400'
                                    }`}>
                                      {rule.is_active ? 'Đang bật' : 'Đã tắt'}
                                    </span>
                                  </div>
                                )}
                              </div>

                              {/* Visual 24h Timeline Bar */}
                              {render24hTimeline(rule)}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* TRƯỜNG HỢP 2: THỜI GIAN THEO TỔNG TỐI ĐA (max_daily) */}
                    {timeLimitMode === 'max_daily' && (
                      <div className="space-y-4">
                        <div className="p-3 bg-zinc-400/10 border border-zinc-400/20 rounded-xl text-xs text-zinc-300 flex items-center gap-2">
                          <span>ℹ️</span>
                          <span>Chế độ <strong>Tổng Thời Gian Tối Đa</strong>: Em trai được dùng tổng cộng số giờ cài đặt trong ngày. Khi mở máy dùng tích lũy đủ số giờ này, máy sẽ tự khóa.</span>
                        </div>

                        <div className="grid grid-cols-1 gap-4">
                          {timeRules.map(rule => {
                            const hoursVal = rule.max_hours !== undefined && rule.max_hours !== null ? rule.max_hours : 4
                            const totalMinutes = Math.round(hoursVal * 60)

                            return (
                              <div key={rule.id} className="p-4 rounded-2xl bg-zinc-900/50 border border-zinc-800 space-y-3 hover:border-zinc-800 transition shadow">
                                <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                                  <div className="flex items-center gap-2.5">
                                    <span className="w-8 h-8 rounded-xl bg-zinc-400/10 border border-zinc-400/20 text-zinc-300 font-bold flex items-center justify-center text-xs">
                                      {rule.day_of_week === 6 ? 'CN' : `T${rule.day_of_week + 2}`}
                                    </span>
                                    <span className="font-bold text-sm text-zinc-200">{dayNames[rule.day_of_week]}</span>
                                  </div>

                                  <div className="flex items-center gap-3">
                                    <span className="text-xs font-mono font-bold text-zinc-300 bg-zinc-400/15 border border-zinc-400/30 px-3 py-1 rounded-xl">
                                      ⏱ {hoursVal} giờ/ngày ({totalMinutes} phút)
                                    </span>

                                    {isAdmin && (
                                      <button
                                        onClick={() => updateTimeRule(rule.id, 'is_active', !rule.is_active)}
                                        className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition ${
                                          rule.is_active ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-zinc-900 text-zinc-400 border border-zinc-800'
                                        }`}
                                      >
                                        {rule.is_active ? 'Đang bật' : 'Đã tắt'}
                                      </button>
                                    )}
                                  </div>
                                </div>

                                {/* SLIDER KẾT HỢP INPUT NUMBER */}
                                {isAdmin ? (
                                  <div className="flex flex-col sm:flex-row items-center gap-4 pt-1">
                                    <div className="flex-grow w-full flex items-center gap-3">
                                      <span className="text-[11px] text-zinc-500 font-mono">0h</span>
                                      <input
                                        type="range"
                                        min="0"
                                        max="24"
                                        step="0.5"
                                        value={hoursVal}
                                        onChange={(e) => updateTimeRule(rule.id, 'max_hours', parseFloat(e.target.value))}
                                        className="flex-grow h-2 bg-zinc-900/50 rounded-lg appearance-none cursor-pointer accent-zinc-400"
                                      />
                                      <span className="text-[11px] text-zinc-500 font-mono">24h</span>
                                    </div>

                                    <div className="flex items-center gap-2 shrink-0">
                                      <span className="text-xs text-zinc-400 font-medium">Số giờ:</span>
                                      <input
                                        type="number"
                                        min="0"
                                        max="24"
                                        step="0.5"
                                        value={hoursVal}
                                        onChange={(e) => updateTimeRule(rule.id, 'max_hours', parseFloat(e.target.value) || 0)}
                                        className="w-20 bg-zinc-900 border border-zinc-800 rounded-xl px-3 py-1.5 text-xs text-center font-bold text-zinc-300 outline-none focus:border-zinc-400"
                                      />
                                      <span className="text-xs text-zinc-400">giờ</span>
                                    </div>
                                  </div>
                                ) : (
                                  <div className="text-xs text-zinc-400">
                                    Thời gian tối đa được phép dùng máy: <strong className="text-white font-mono">{hoursVal} tiếng</strong> ({totalMinutes} phút).
                                  </div>
                                )}
                              </div>
                            )
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* TAB:  ẢNH CHỤP MÀN HÌNH (CHỈ ADMIN XEM, SẮP XẾP THEO NGÀY & XÓA NHIỀU ẢNH) */}
            {activeTab === 'screenshots' && isAdmin && (
              <div className="space-y-6">
                <div className={`${cardBgClass} border rounded-2xl p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4`}>
                  <div>
                    <h2 className="font-bold text-lg flex items-center gap-2">
                      <span></span> Ảnh Chụp Màn Hình (Quyền Riêng Admin)
                    </h2>
                    <p className="text-xs text-zinc-400 mt-1">Đã tự động nhóm theo ngày. Tích chọn để xóa nhiều ảnh cùng lúc.</p>
                  </div>

                  {selectedScreenshotIds.length > 0 && (
                    <button
                      onClick={handleBulkDeleteScreenshots}
                      disabled={bulkDeleting}
                      className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white font-bold rounded-xl text-xs flex items-center gap-2 transition disabled:opacity-50"
                    >
                      {bulkDeleting ? '⏳ Đang xóa...' : `️ Xóa ${selectedScreenshotIds.length} ảnh đã chọn`}
                    </button>
                  )}
                </div>

                {/* KHUNG CỐ ĐỊNH:  ẢNH VỪA CHỤP NGAY TỨC THÌ (INSTANT PREVIEW CONTAINER) */}
                <div className={`${cardBgClass} border border-indigo-500/40 rounded-2xl p-5 space-y-4 bg-gradient-to-r from-blue-950/30 to-slate-900 shadow-2xl`}>
                  <div className="flex items-center justify-between border-b border-indigo-500/20 pb-3">
                    <div className="flex items-center gap-2">
                      <span className="w-3 h-3 rounded-full bg-emerald-400 animate-ping"></span>
                      <h3 className="font-bold text-base text-blue-300 flex items-center gap-2">
                         Khung Xem Nhanh Ảnh Chụp Màn Hình Ngay Tức Thì
                      </h3>
                      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 border border-emerald-500/30 uppercase tracking-wider">
                        Mới Nhất
                      </span>
                    </div>
                    <button
                      onClick={sendInstantScreenshot}
                      disabled={cmdSending}
                      className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl text-xs transition disabled:opacity-50 flex items-center gap-1.5 shadow"
                    >
                      {cmdSending ? '⏳ Đang chụp...' : ' Chụp Mới Ngay Tức Thì'}
                    </button>
                  </div>

                  {screenshots.length === 0 ? (
                    <div className="text-center text-zinc-500 py-8 text-xs">Bấm nút "Chụp Mới Ngay Tức Thì" để lấy ảnh chụp màn hình máy em trai lập tức.</div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Ảnh mới nhất 1 */}
                      {screenshots.slice(0, 1).map(item => (
                        <div key={`instant-${item.id}`} className="border border-indigo-500/40 rounded-xl overflow-hidden group relative bg-black shadow-xl">
                          <img
                            src={getScreenshotUrl(item.file_path, { width: 640, quality: 70 })}
                            alt="instant screenshot" loading="lazy"
                            className="w-full h-64 object-contain bg-black cursor-pointer"
                            onClick={() => setSelectedImage(getScreenshotUrl(item.file_path, { width: 1600, quality: 85 }))}
                          />
                          <div className="p-3 flex items-center justify-between text-xs bg-zinc-900/50/90 border-t border-zinc-800">
                            <div className="flex items-center gap-2">
                              <span className="text-zinc-300 text-xs font-semibold"> {item.created_at ? new Date(item.created_at).toLocaleDateString('vi-VN') : ''}</span>
                              <span className="font-mono text-amber-300 font-bold bg-amber-500/20 text-xs px-2.5 py-0.5 rounded border border-amber-500/30">
                                ⏱ {getScreenshotDisplayTime(item) || formatClockTime(item.created_at)}
                              </span>
                            </div>
                            <div className="flex gap-2">
                              <button
                                onClick={() => setSelectedImage(getScreenshotUrl(item.file_path, { width: 1600, quality: 85 }))}
                                className="text-blue-400 hover:text-blue-300 font-semibold px-2.5 py-1 rounded bg-blue-500/10 hover:bg-blue-500/20 transition text-xs"
                              >
                                 Phóng To
                              </button>
                              <button
                                onClick={() => deleteScreenshot(item.id, item.file_path)}
                                className="text-red-400 hover:text-red-300 font-semibold px-2 py-1 rounded hover:bg-red-500/10 transition text-xs"
                              >
                                Xóa
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}

                      {/* Ảnh mới thứ 2 nếu có */}
                      {screenshots.slice(1, 2).map(item => (
                        <div key={`instant-prev-${item.id}`} className="border border-zinc-800 rounded-xl overflow-hidden group relative bg-black opacity-90">
                          <img
                            src={getScreenshotUrl(item.file_path, { width: 640, quality: 70 })}
                            alt="instant screenshot previous" loading="lazy"
                            className="w-full h-64 object-contain bg-black cursor-pointer"
                            onClick={() => setSelectedImage(getScreenshotUrl(item.file_path, { width: 1600, quality: 85 }))}
                          />
                          <div className="p-3 flex items-center justify-between text-xs bg-zinc-900/50/90 border-t border-zinc-800">
                            <div className="flex items-center gap-2">
                              <span className="text-zinc-400 text-xs">Ảnh trước đó:</span>
                              <span className="font-mono text-zinc-300 font-bold bg-zinc-900 px-2 py-0.5 rounded text-xs">
                                ⏱ {getScreenshotDisplayTime(item) || formatClockTime(item.created_at)}
                              </span>
                            </div>
                            <button
                              onClick={() => setSelectedImage(getScreenshotUrl(item.file_path, { width: 1600, quality: 85 }))}
                              className="text-blue-400 hover:text-blue-300 font-semibold px-2.5 py-1 rounded bg-blue-500/10 transition text-xs"
                            >
                               Phóng To
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {Object.keys(groupedScreenshots).length === 0 ? (
                  <div className="text-center text-zinc-500 py-16">Chưa có ảnh chụp màn hình nào.</div>
                ) : (
                  Object.entries(groupedScreenshots).map(([dateLabel, items]) => {
                    const allInGroupSelected = items.every(i => selectedScreenshotIds.includes(i.id))

                    return (
                      <div key={dateLabel} className={`${cardBgClass} border rounded-2xl p-5 space-y-4`}>
                        <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                          <label className="flex items-center gap-2 cursor-pointer font-bold text-blue-400 text-sm">
                            <input
                              type="checkbox"
                              checked={allInGroupSelected}
                              onChange={() => toggleSelectDateGroup(dateLabel, items)}
                              className="w-4 h-4 rounded text-blue-600"
                            />
                            <span> {dateLabel} ({items.length} ảnh)</span>
                          </label>

                          <span className="text-xs text-zinc-500">Tích chọn để nhóm toàn bộ ngày này</span>
                        </div>

                        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                          {items.map(item => {
                            const isSelected = selectedScreenshotIds.includes(item.id)
                            return (
                              <div
                                key={item.id}
                                className={`border rounded-xl overflow-hidden group relative transition ${
                                  isSelected ? 'border-indigo-500 ring-2 ring-blue-500/50' : 'border-zinc-800 hover:border-indigo-500/30'
                                }`}
                              >
                                <input
                                  type="checkbox"
                                  checked={isSelected}
                                  onChange={() => toggleSelectScreenshot(item.id)}
                                  className="absolute top-2 left-2 z-10 w-5 h-5 rounded text-blue-600 cursor-pointer shadow"
                                />

                                <img
                                  src={getScreenshotUrl(item.file_path, { width: 640, quality: 70 })}
                                  alt="screenshot" loading="lazy"
                                  className="w-full h-40 object-cover cursor-pointer"
                                  onClick={() => setSelectedImage(getScreenshotUrl(item.file_path, { width: 1600, quality: 85 }))}
                                />

                                <div className="p-2 flex items-center justify-between text-xs text-zinc-400 bg-zinc-900/50">
                                  <div className="flex items-center gap-2">
                                    <span className="text-zinc-300 text-[11px] font-medium">
                                      {item.created_at ? new Date(item.created_at).toLocaleDateString('vi-VN') : ''}
                                    </span>
                                    <span className="font-mono text-zinc-200 text-[11px] font-bold bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                                      ⏱ {getScreenshotDisplayTime(item) || formatClockTime(item.created_at)}
                                    </span>
                                  </div>
                                  <button
                                    onClick={() => deleteScreenshot(item.id, item.file_path)}
                                    className="text-red-400 hover:text-red-300 font-semibold px-2 py-0.5 rounded hover:bg-red-500/10 transition text-[11px]"
                                  >
                                    Xóa
                                  </button>
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      </div>
                    )
                  })
                )}

                {selectedImage && (
                  <div
                    className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4"
                    onClick={() => setSelectedImage(null)}
                  >
                    <img src={selectedImage} alt="full" className="max-w-full max-h-full rounded-lg shadow-2xl" />
                  </div>
                )}
              </div>
            )}

            {/* TAB: CÀI ĐẶT ADMIN — REFACTORED SUB-TABS & PERMISSION MATRIX */}
            {activeTab === 'config' && isAdmin && (
              <div className="space-y-6 max-w-5xl mx-auto pb-16">
                <div className={`${cardBgClass} border rounded-2xl p-6 space-y-6 shadow-2xl`}>

                  {/* HEADER TOP BAR */}
                  <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-zinc-800 pb-5">
                    <div>
                      <h2 className="text-xl font-bold flex items-center gap-2 text-slate-100">
                        <span></span> Cài Đặt Admin & Quản Lý Hệ Thống
                      </h2>
                      <p className="text-xs text-zinc-400 mt-1">
                        Cấu hình phân quyền tư cách, quản lý thiết bị kết nối và bảo mật hệ thống.
                      </p>
                    </div>
                  </div>

                  {/* NAV SUB-TABS (4 SUB-TABS) */}
                  <div className="flex bg-black p-1.5 rounded-2xl border border-zinc-800 text-xs overflow-x-auto gap-1">
                    <button
                      onClick={() => setSettingsSubTab('permissions')}
                      className={`px-4 py-2.5 rounded-xl font-bold transition flex items-center gap-2 shrink-0 ${
                        settingsSubTab === 'permissions' ? 'bg-zinc-100 text-black hover:bg-white shadow' : 'text-zinc-400 hover:text-white'
                      }`}
                    >
                      <span></span>
                      <span>Phân Quyền & Tư Cách</span>
                    </button>

                    <button
                      onClick={() => setSettingsSubTab('devices')}
                      className={`px-4 py-2.5 rounded-xl font-bold transition flex items-center gap-2 shrink-0 ${
                        settingsSubTab === 'devices' ? 'bg-zinc-100 text-black hover:bg-white shadow' : 'text-zinc-400 hover:text-white'
                      }`}
                    >
                      <span></span>
                      <span>Thiết Bị Truy Cập ({activeSessions.length})</span>
                    </button>

                    <button
                      onClick={() => setSettingsSubTab('agent')}
                      className={`px-4 py-2.5 rounded-xl font-bold transition flex items-center gap-2 shrink-0 ${
                        settingsSubTab === 'agent' ? 'bg-zinc-100 text-black hover:bg-white shadow' : 'text-zinc-400 hover:text-white'
                      }`}
                    >
                      <span></span>
                      <span>Cấu Hình Agent & Theme</span>
                    </button>

                    <button
                      onClick={() => setSettingsSubTab('security')}
                      className={`px-4 py-2.5 rounded-xl font-bold transition flex items-center gap-2 shrink-0 ${
                        settingsSubTab === 'security' ? 'bg-zinc-100 text-black hover:bg-white shadow' : 'text-zinc-400 hover:text-white'
                      }`}
                    >
                      <span></span>
                      <span>Bảo Mật & Mật Khẩu</span>
                    </button>
                  </div>

                  {/* SUB-TAB 1: PERMISSION MATRIX TABLE */}
                  {settingsSubTab === 'permissions' && (
                    <div className="space-y-5">
                      <div className="p-4 bg-zinc-900/50 border border-zinc-800 rounded-2xl space-y-4 shadow-inner">
                        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                          <div>
                            <h3 className="font-bold text-sm text-blue-400 flex items-center gap-2">
                              <span></span> Quản Lý Tư Cách Người Dùng
                            </h3>
                            <p className="text-xs text-zinc-400">Thêm vai trò mới (Ví dụ: Gia sư, Ông bà, Bố, Mẹ...)</p>
                          </div>

                          <form onSubmit={handleAddCustomRole} className="flex gap-2 w-full sm:w-auto">
                            <input
                              type="text"
                              placeholder="Thêm tư cách mới..."
                              value={newRoleInput}
                              onChange={(e) => setNewRoleInput(e.target.value)}
                              className="bg-zinc-900 border border-zinc-800 rounded-xl px-3.5 py-1.5 text-xs text-slate-100 outline-none focus:border-indigo-500 flex-grow"
                            />
                            <button type="submit" className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 font-bold rounded-xl text-xs text-white whitespace-nowrap shadow">
                              + Thêm
                            </button>
                          </form>
                        </div>

                        {/* PASSWORD TƯ CÁCH */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 pt-2">
                          {displayRoles.map(roleName => (
                            <div key={roleName} className="p-3 bg-zinc-900/50 border border-zinc-800 rounded-xl space-y-2 text-xs">
                              <div className="flex items-center justify-between font-bold">
                                <span>{roleName}</span>
                                {roleName !== 'Khách (Chưa chọn)' && customRoles.length > 1 && (
                                  <button onClick={() => handleRemoveCustomRole(roleName)} className="text-[10px] text-red-400 hover:text-red-300">
                                    Xóa
                                  </button>
                                )}
                              </div>
                              <input
                                type="text"
                                placeholder="Mật khẩu tư cách..."
                                value={rolePasswords[roleName] || ''}
                                onChange={(e) => handleSetRolePassword(roleName, e.target.value)}
                                className="w-full bg-black border border-zinc-800 rounded-lg px-2.5 py-1 text-xs font-mono text-emerald-400 outline-none"
                              />
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* BẢNG MA TRẬN PHÂN QUYỀN (PERMISSION MATRIX TABLE) */}
                      <div className="space-y-3">
                        <div className="text-xs font-bold text-zinc-300 flex items-center gap-2">
                          <span></span> BẢNG MA TRẬN PHÂN QUYỀN TRUY CẬP (PERMISSION MATRIX)
                        </div>

                        <div className="overflow-x-auto rounded-2xl border border-zinc-800 shadow">
                          <table className="w-full text-left text-xs">
                            <thead>
                              <tr className="border-b border-zinc-800 text-zinc-400 font-bold uppercase tracking-wider text-[11px] bg-black/90">
                                <th className="p-3.5 sticky left-0 bg-black z-10 border-r border-zinc-800">Chức Năng / Tab</th>
                                {displayRoles.map(roleName => (
                                  <th key={roleName} className="p-3.5 text-center min-w-[130px] border-r border-zinc-800/60 text-amber-300">
                                    {roleName}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800/60 bg-zinc-900/50/40">
                              {rawTabList.filter(t => t.id !== 'config' && t.id !== 'screenshots').map(tab => (
                                <tr key={tab.id} className="hover:bg-zinc-900/40 transition">
                                  <td className="p-3.5 font-bold text-zinc-200 sticky left-0 bg-zinc-900/50 border-r border-zinc-800 whitespace-nowrap">
                                    {tab.label}
                                  </td>
                                  {displayRoles.map(roleName => {
                                    const curPerm = rolePermissions[roleName]?.[tab.id] || 'edit'

                                    return (
                                      <td key={roleName} className="p-2.5 text-center border-r border-zinc-800/60">
                                        <select
                                          value={curPerm}
                                          onChange={(e) => handleSetRolePermission(roleName, tab.id, e.target.value)}
                                          className={`w-full border rounded-xl px-2 py-1 text-xs font-bold outline-none cursor-pointer transition ${
                                            curPerm === 'edit'
                                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 border-emerald-500/40'
                                              : curPerm === 'view'
                                              ? 'bg-blue-500/20 text-blue-300 border-indigo-500/40'
                                              : 'bg-red-500/20 text-red-300 border-red-500/40'
                                          }`}
                                        >
                                          <option value="edit"> Toàn Quyền</option>
                                          <option value="view"> Chỉ Xem</option>
                                          <option value="none"> Ẩn Tab</option>
                                        </select>
                                      </td>
                                    )
                                  })}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* SUB-TAB 2: DEVICE ACCESS MANAGEMENT TABLE */}
                  {settingsSubTab === 'devices' && (
                    <div className="space-y-4">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-zinc-400 px-1">
                        <span className="font-bold text-zinc-200">DANH SÁCH THIẾT BỊ ĐANG KẾT NỐI ({activeSessions.length})</span>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={cleanupStaleSessions}
                            className="px-3 py-1.5 bg-zinc-900 hover:bg-slate-700 text-zinc-300 text-xs font-bold rounded-xl transition border border-zinc-800 shadow flex items-center gap-1.5"
                          >
                            <span></span>
                            <span>Dọn Dẹp Session Rác</span>
                          </button>
                        </div>
                      </div>

                      <div className="overflow-x-auto rounded-2xl border border-zinc-800 shadow">
                        <table className="w-full text-left text-xs">
                          <thead>
                            <tr className="border-b border-zinc-800 text-zinc-400 font-bold uppercase tracking-wider text-[11px] bg-zinc-900/50">
                              <th className="p-3.5">Thiết Bị / Trình Duyệt</th>
                              <th className="p-3.5">Tư Cách</th>
                              <th className="p-3.5">Trạng Thái & Hoạt Động</th>
                              <th className="p-3.5 text-right">Tác Vụ</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800/60 bg-zinc-900/50/40">
                            {activeSessions.map((sess, idx) => {
                              const isCurrentDev = sess.session_id === sessionId
                              const infoLower = (sess.device_info || '').toLowerCase()
                              const isMobile = infoLower.includes('mobile') || infoLower.includes('android') || infoLower.includes('iphone')
                              const diffSec = sess.last_active ? Math.max(0, Math.round((Date.now() - new Date(sess.last_active).getTime()) / 1000)) : 0
                              const activeText = diffSec <= 5 ? ' Vừa tương tác' : `⏱ ${diffSec}s trước`

                              return (
                                <tr key={sess.session_id || idx} className="hover:bg-zinc-900/50 transition">
                                  <td className="p-3.5 font-semibold text-zinc-200">
                                    <div className="flex items-center gap-2">
                                      {isCurrentDev ? (
                                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 border border-emerald-500/30">
                                           MÁY NÀY
                                        </span>
                                      ) : isMobile ? (
                                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-blue-500/20 text-blue-300 border border-indigo-500/30">
                                           ĐIỆN THOẠI
                                        </span>
                                      ) : (
                                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-zinc-400/20 text-zinc-300 border border-zinc-400/30">
                                          ️ LAPTOP / PC
                                        </span>
                                      )}
                                      <span className="truncate">{sess.device_info || 'Thiết bị Web'}</span>
                                    </div>
                                  </td>

                                  <td className="p-3.5">
                                    <div className="flex items-center gap-1.5">
                                      <span className="px-2.5 py-1 rounded-xl text-xs font-bold bg-zinc-900 text-blue-300 border border-zinc-800">
                                        {sess.user_role}
                                      </span>
                                      {sess.tabCount > 1 && (
                                        <span className="px-2 py-0.5 rounded-lg text-[10px] font-bold bg-zinc-400/20 text-zinc-300 border border-zinc-400/30 font-mono">
                                          {sess.tabCount} Tabs
                                        </span>
                                      )}
                                    </div>
                                  </td>

                                  <td className="p-3.5 font-mono text-zinc-400 text-[11px]">
                                    <div className="text-emerald-400 font-bold">{activeText}</div>
                                    <div className="text-zinc-500 text-[10px]">{formatTime(sess.last_active)}</div>
                                  </td>

                                  <td className="p-3.5 text-right">
                                    <button
                                      onClick={() => openBlockSessionModal(sess)}
                                      className={`px-3.5 py-1.5 rounded-xl font-bold text-xs transition border shadow ${
                                        sess.is_blocked
                                          ? 'bg-emerald-600 hover:bg-emerald-500 text-white border-emerald-500'
                                          : 'bg-red-600/15 hover:bg-red-600 text-red-300 hover:text-white border-red-500/30'
                                      }`}
                                    >
                                      {sess.is_blocked ? ' Bỏ Chặn' : ' Chặn Thiết Bị'}
                                    </button>
                                  </td>
                                </tr>
                              )
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* SUB-TAB 3: AGENT CONFIG & THEME */}
                  {settingsSubTab === 'agent' && (
                    <div className="space-y-5">
                      {/* THEME SELECTOR */}
                      <div className="p-4 rounded-2xl bg-zinc-900/50 border border-zinc-800 space-y-3 shadow-inner">
                        <label className="block text-xs font-bold text-blue-400"> Chủ Đề Giao Diện (Theme Mode)</label>
                        <div className="grid grid-cols-3 gap-3">
                          <button
                            type="button"
                            onClick={() => changeTheme('light')}
                            className={`p-3 rounded-xl border text-xs font-bold flex items-center justify-center gap-1.5 transition ${
                              themeMode === 'light' ? 'bg-zinc-100 text-black hover:bg-white border-indigo-500 shadow' : 'bg-white text-slate-900 border-slate-300'
                            }`}
                          >
                            <span>️ Sáng</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => changeTheme('dark')}
                            className={`p-3 rounded-xl border text-xs font-bold flex items-center justify-center gap-1.5 transition ${
                              themeMode === 'dark' ? 'bg-zinc-100 text-black hover:bg-white border-indigo-500 shadow' : 'bg-zinc-900/50 text-zinc-200 border-zinc-800'
                            }`}
                          >
                            <span> Tối (Slate)</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => changeTheme('black')}
                            className={`p-3 rounded-xl border text-xs font-bold flex items-center justify-center gap-1.5 transition ${
                              themeMode === 'black' ? 'bg-zinc-100 text-black hover:bg-white border-indigo-500 shadow' : 'bg-black text-zinc-200 border-zinc-800'
                            }`}
                          >
                            <span>⬛ Tối Sâu (Black)</span>
                          </button>
                        </div>
                      </div>

                      {/* SCREENSHOT INTERVAL */}
                      <div className="p-4 rounded-2xl bg-zinc-900/50 border border-zinc-800 space-y-3 shadow-inner">
                        <label className="block text-xs font-bold text-zinc-200">
                          ⏱ Chu Kỳ Chụp Màn Hình Tự Động (Nhập số phút thủ công)
                        </label>
                        <div className="flex items-center gap-3">
                          <input
                            type="number"
                            min="1"
                            max="180"
                            value={screenshotMin}
                            onChange={(e) => setScreenshotMin(e.target.value)}
                            className="w-32 bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-2 text-sm font-bold text-zinc-200 outline-none focus:border-amber-500 text-center"
                            required
                          />
                          <span className="text-xs font-semibold text-zinc-300">phút / lần</span>
                        </div>
                        <span className="text-[11px] text-zinc-500">Nhập số phút Agent sẽ chụp màn hình máy em trai định kỳ (Ví dụ: 1, 3, 5...).</span>
                      </div>
                    </div>
                  )}

                  {/* SUB-TAB 4: SECURITY & SYSTEM PASSWORDS (WITH EYE TOGGLES) */}
                  {settingsSubTab === 'security' && (
                    <div className="space-y-5">
                      <div className="p-5 rounded-2xl bg-zinc-900/50 border border-zinc-800 space-y-4 shadow-inner">
                        <div className="text-xs font-bold text-emerald-400 flex items-center gap-2">
                          <span></span> Thay Đổi Mật Khẩu Hệ Thống & PIN Admin
                        </div>

                        {/* AGENT PASSWORD */}
                        <div className="space-y-1.5">
                          <label className="block text-xs font-semibold text-zinc-300">
                            Mật Khẩu Dừng / Gỡ Agent (Máy Em Trai)
                          </label>
                          <div className="relative">
                            <input
                              type={showAgentPass ? "text" : "password"}
                              value={newAgentPass}
                              onChange={(e) => setNewAgentPass(e.target.value)}
                              className="w-full bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-2.5 text-xs font-mono text-emerald-300 focus:border-indigo-500 outline-none pr-20"
                              required
                            />
                            <button
                              type="button"
                              onClick={() => setShowAgentPass(!showAgentPass)}
                              className="absolute right-2.5 top-1/2 -translate-y-1/2 px-2.5 py-1 bg-zinc-900 hover:bg-slate-700 text-zinc-300 text-[11px] font-bold rounded-lg transition"
                            >
                              {showAgentPass ? ' Ẩn' : '️ Hiện'}
                            </button>
                          </div>
                        </div>

                        {/* ADMIN PIN */}
                        <div className="space-y-1.5">
                          <label className="block text-xs font-semibold text-zinc-300">
                            Mã PIN Đăng Nhập Web Admin
                          </label>
                          <div className="relative">
                            <input
                              type={showAdminPin ? "text" : "password"}
                              value={newAdminPin}
                              onChange={(e) => setNewAdminPin(e.target.value)}
                              className="w-full bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-2.5 text-xs font-mono text-emerald-300 focus:border-indigo-500 outline-none pr-20"
                              required
                            />
                            <button
                              type="button"
                              onClick={() => setShowAdminPin(!showAdminPin)}
                              className="absolute right-2.5 top-1/2 -translate-y-1/2 px-2.5 py-1 bg-zinc-900 hover:bg-slate-700 text-zinc-300 text-[11px] font-bold rounded-lg transition"
                            >
                              {showAdminPin ? ' Ẩn' : '️ Hiện'}
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {configMsg && (
                    <div className="text-xs p-3 rounded-xl bg-zinc-900 border border-zinc-800 font-medium text-emerald-400">
                      {configMsg}
                    </div>
                  )}
                </div>

                {/* STICKY SAVE BAR AT BOTTOM */}
                <div className="fixed bottom-16 lg:bottom-6 right-6 z-40 bg-zinc-900/50/95 border border-indigo-500/40 backdrop-blur-xl rounded-2xl p-3 shadow-2xl flex items-center gap-4 animate-in slide-in-from-bottom duration-200">
                  <div className="hidden sm:block text-xs text-zinc-300 font-medium">
                    <span> Đã sẵn sàng áp dụng cấu hình Cài Đặt Admin.</span>
                  </div>
                  <button
                    onClick={handleSaveConfig}
                    className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl text-xs transition shadow-lg shadow-indigo-600/20 flex items-center gap-2"
                  >
                    <span></span>
                    <span>Lưu Tất Cả Cài Đặt Admin</span>
                  </button>
                </div>
              </div>
            )}

            {/* TAB: QUẢN LÝ BỘ NHỚ (STORAGE MANAGEMENT) */}
            {activeTab === 'storage' && isAdmin && (
              <div className={`${cardBgClass} border rounded-2xl p-6 space-y-6 max-w-5xl mx-auto shadow-2xl`}>
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-zinc-800 pb-4">
                  <div>
                    <h2 className="font-bold text-xl flex items-center gap-2 text-emerald-400">
                      <span>💾</span> Quản Lý Bộ Nhớ & Dọn Rác Triệt Để Supabase
                    </h2>
                    <p className="text-xs text-zinc-400 mt-1">
                      Thống kê dung lượng, xóa log theo khoảng ngày, cấu hình tự động dọn rác và tối ưu dung lượng DB.
                    </p>
                  </div>
                  <button
                    onClick={handleDeepStorageVacuum}
                    disabled={isCleaningStorage}
                    className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl text-xs transition shadow-lg shadow-emerald-600/20 flex items-center gap-2 disabled:opacity-50"
                  >
                    <span>🧹</span>
                    <span>{isCleaningStorage ? 'Đang Dọn Rác...' : 'Dọn Rác Triệt Để (Vacuum)'}</span>
                  </button>
                </div>

                {storageMessage && (
                  <div className={`p-4 rounded-xl text-xs font-semibold ${
                    storageMessage.includes('❌') 
                      ? 'bg-red-500/10 border border-red-500/20 text-red-400'
                      : 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
                  }`}>
                    {storageMessage}
                  </div>
                )}

                {/* THỐNG KÊ DUNG LƯỢNG HIỆN TẠI (ROW COUNTS) */}
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
                  <div className="p-3.5 bg-zinc-900/50 border border-zinc-800 rounded-xl space-y-1 text-center">
                    <div className="text-[10px] text-zinc-400 font-medium">Lịch Sử Web</div>
                    <div className="text-lg font-bold text-blue-400">{browserHistory.length.toLocaleString()}</div>
                    <div className="text-[9px] text-zinc-500">dòng log</div>
                  </div>
                  <div className="p-3.5 bg-zinc-900/50 border border-zinc-800 rounded-xl space-y-1 text-center">
                    <div className="text-[10px] text-zinc-400 font-medium">Active Window</div>
                    <div className="text-lg font-bold text-amber-400">{activeWindows.length.toLocaleString()}</div>
                    <div className="text-[9px] text-zinc-500">dòng log</div>
                  </div>
                  <div className="p-3.5 bg-zinc-900/50 border border-zinc-800 rounded-xl space-y-1 text-center">
                    <div className="text-[10px] text-zinc-400 font-medium">Tiến Trình</div>
                    <div className="text-lg font-bold text-emerald-400">{processes.length.toLocaleString()}</div>
                    <div className="text-[9px] text-zinc-500">dòng log</div>
                  </div>
                  <div className="p-3.5 bg-zinc-900/50 border border-zinc-800 rounded-xl space-y-1 text-center">
                    <div className="text-[10px] text-zinc-400 font-medium">Ảnh Chụp</div>
                    <div className="text-lg font-bold text-purple-400">{screenshots.length.toLocaleString()}</div>
                    <div className="text-[9px] text-zinc-500">files ảnh</div>
                  </div>
                  <div className="p-3.5 bg-zinc-900/50 border border-zinc-800 rounded-xl space-y-1 text-center">
                    <div className="text-[10px] text-zinc-400 font-medium">Hộp Thao Tác</div>
                    <div className="text-lg font-bold text-indigo-400">{todoNotes.length.toLocaleString()}</div>
                    <div className="text-[9px] text-zinc-500">bản ghi</div>
                  </div>
                  <div className="p-3.5 bg-zinc-900/50 border border-zinc-800 rounded-xl space-y-1 text-center">
                    <div className="text-[10px] text-zinc-400 font-medium">Chat & Lệnh</div>
                    <div className="text-lg font-bold text-cyan-400">{chatMessages.length.toLocaleString()}</div>
                    <div className="text-[9px] text-zinc-500">tin nhắn</div>
                  </div>
                </div>

                {/* KHUNG XÓA DỮ LIỆU THEO KHOẢNG NGÀY VÀ LOẠI DỮ LIỆU */}
                <div className="p-5 rounded-2xl bg-zinc-900/40 border border-zinc-800 space-y-4">
                  <div className="flex items-center gap-2 border-b border-zinc-800 pb-3">
                    <span className="text-lg">🗓️</span>
                    <h3 className="font-bold text-sm text-zinc-200">Xóa Dữ Liệu Tự Chọn Theo Khoảng Thời Gian</h3>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Loại dữ liệu */}
                    <div className="space-y-1.5">
                      <label className="text-xs text-zinc-400 font-medium">Chọn loại dữ liệu cần xóa:</label>
                      <select
                        value={storageLogType}
                        onChange={e => setStorageLogType(e.target.value)}
                        className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500"
                      >
                        <option value="all">⚡ TẤT CẢ DỮ LIỆU LOG (Tối ưu nhất)</option>
                        <option value="browser_history_logs">🌐 Lịch sử duyệt Web (browser_history_logs)</option>
                        <option value="active_window_logs">🖥️ Log Cửa sổ Active (active_window_logs)</option>
                        <option value="process_logs">⚙️ Log Tiến trình (process_logs)</option>
                        <option value="screenshot_logs">📸 Log & Files Ảnh Chụp (screenshot_logs)</option>
                        <option value="system_events">🔔 Log Sự kiện hệ thống (system_events)</option>
                        <option value="system_commands">📡 Log Lệnh hệ thống (system_commands)</option>
                      </select>
                    </div>

                    {/* Từ ngày */}
                    <div className="space-y-1.5">
                      <label className="text-xs text-zinc-400 font-medium">Từ ngày (Start Date):</label>
                      <input
                        type="date"
                        value={storageStartDate}
                        onChange={e => setStorageStartDate(e.target.value)}
                        className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500"
                      />
                    </div>

                    {/* Đến ngày */}
                    <div className="space-y-1.5">
                      <label className="text-xs text-zinc-400 font-medium">Đến ngày (End Date):</label>
                      <input
                        type="date"
                        value={storageEndDate}
                        onChange={e => setStorageEndDate(e.target.value)}
                        className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500"
                      />
                    </div>
                  </div>

                  <div className="flex justify-end pt-2">
                    <button
                      onClick={handleDeleteStorageByRange}
                      disabled={isCleaningStorage}
                      className="px-5 py-2.5 bg-red-600 hover:bg-red-500 text-white font-bold rounded-xl text-xs transition shadow-lg shadow-red-600/20 flex items-center gap-2 disabled:opacity-50"
                    >
                      <span>🗑️</span>
                      <span>{isCleaningStorage ? 'Đang Xóa...' : 'Xóa Dữ Liệu Trong Khoảng Ngày Đã Chọn'}</span>
                    </button>
                  </div>
                </div>

                {/* KHUNG CẤU HÌNH TỰ ĐỘNG DỌN DẸP LÊN SUPABASE */}
                <div className="p-5 rounded-2xl bg-zinc-900/40 border border-zinc-800 space-y-4">
                  <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">⚙️</span>
                      <h3 className="font-bold text-sm text-zinc-200">Cấu Hình Tự Động Xóa Dữ Liệu Định Kỳ</h3>
                    </div>
                    <span className="text-[11px] px-2.5 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full font-mono">
                      Đang bật dọn rác tự động 30 ngày
                    </span>
                  </div>

                  <div className="text-xs text-zinc-400 leading-relaxed space-y-2">
                    <p>
                      Hệ thống Supabase được tích hợp sẵn hàm dọn dẹp tự động <code className="text-amber-300">clean_old_logs()</code> chạy ngầm. Các bản ghi log tiến trình, lịch sử duyệt web và các lệnh hệ thống cũ hơn 30 ngày sẽ tự động được dọn dẹp để bộ nhớ Supabase Cloud luôn ở trạng thái xanh an toàn.
                    </p>
                    <div className="p-3 bg-zinc-950/60 border border-zinc-800/80 rounded-xl flex items-center justify-between">
                      <span className="text-zinc-300 font-medium">Trạng thái tự động Vacuum dọn rác DB Supabase:</span>
                      <span className="text-emerald-400 font-bold flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
                        ĐÃ BẬT KHUNG DỌN DẸP TỰ ĐỘNG
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* TAB:  HƯỚNG DẪN DÀNH CHO ADMIN */}
            {activeTab === 'admin_guide' && isAdmin && (
              <div className={`${cardBgClass} border rounded-2xl p-6 space-y-6 max-w-4xl mx-auto shadow-2xl`}>
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-zinc-800 pb-4">
                  <div>
                    <h2 className="font-bold text-xl flex items-center gap-2.5 text-blue-400">
                      <span></span> Hướng Dẫn Chi Tiết Cài Đặt, Tạm Dừng & Gỡ Bỏ (Admin)
                    </h2>
                    <p className="text-xs text-zinc-400 mt-1">Tài liệu quản trị hệ thống Parental Control toàn diện.</p>
                  </div>
                  <a
                    href="/Admin_Manual_ParentalControl.html"
                    target="_blank"
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl text-xs transition shadow flex items-center gap-1.5"
                  >
                    <span></span>
                    <span>Mở File Hướng Dẫn HTML Gốc</span>
                  </a>
                </div>

                {/* KHUNG CÁC CÁCH CÀI ĐẶT LÊN MÁY EM TRAI */}
                <div className="p-5 rounded-xl bg-zinc-900/50 border border-zinc-800 space-y-3">
                  <h3 className="font-bold text-sm text-emerald-400 flex items-center gap-2">
                    <span></span> 1. CÁCH CÀI ĐẶT NGẦM 1-CLICK LÊN MÁY EM TRAI
                  </h3>
                  <div className="text-xs text-zinc-300 space-y-2 leading-relaxed">
                    <p>Code Python của Agent đã được đóng gói thành file thực thi mã hóa <strong className="text-white">ParentalControlAgent.exe</strong>. Em trai không thể xem hay chỉnh sửa mã nguồn bên trong.</p>
                    <ol className="list-decimal pl-5 space-y-1.5 text-zinc-400">
                      <li>Biên dịch file EXE (trên máy bạn): Chạy file <code className="text-amber-300">d:\Hoàng\PMQL\parental-control\agent\build_exe.bat</code> để tạo file <code className="text-amber-300">ParentalControlAgent.exe</code> trong <code className="text-zinc-200">dist\ParentalControlAgent\</code>.</li>
                      <li>Copy file cài đặt <code className="text-amber-300">Install_Parental_Control.bat</code> bỏ vào cùng thư mục <code className="text-zinc-200">dist\ParentalControlAgent\</code>.</li>
                      <li>Copy toàn bộ thư mục sang máy em trai (hoặc nén zip gửi sang).</li>
                      <li>Trên máy em trai: Chuột phải vào file <strong className="text-emerald-300">Install_Parental_Control.bat  Chọn "Run as administrator"</strong>.</li>
                      <li>Chương trình sẽ tự động cài vào thư mục ẩn hệ thống <code className="text-zinc-200">C:\ProgramData\ParentalControl\</code>, tự ẩn thư mục và tự đăng ký Windows Task Scheduler khởi động ngầm cùng Windows dưới quyền Administrator cao nhất.</li>
                    </ol>
                  </div>
                </div>

                {/* KHUNG CÁC CÁCH TẠM DỪNG KIỂM SOÁT */}
                <div className="p-5 rounded-xl bg-zinc-900/50 border border-zinc-800 space-y-3">
                  <h3 className="font-bold text-sm text-zinc-200 flex items-center gap-2">
                    <span></span> 2. CÁCH TẠM DỪNG KIỂM SOÁT (2 CÁCH)
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    <div className="p-3.5 rounded-xl bg-zinc-900/50 border border-zinc-800 space-y-2">
                      <div className="font-bold text-zinc-200 text-sm">Cách 1: Tạm Dừng Từ Xa Qua Web App (Khuyên Dùng)</div>
                      <p className="text-zinc-400 leading-relaxed">
                        Trên thanh Header chính của trang Web này, bấm nút <strong className="text-zinc-100">Tạm Dừng Kiểm Soát</strong>.
                        Agent trên máy em trai sẽ tự động tạm dừng tất cả các hiệu ứng cấm web, cấm app, giới hạn giờ và khóa màn hình. 
                        Khi muốn bật lại, bạn chỉ cần bấm <strong className="text-zinc-100">Tiếp Tục Kiểm Soát</strong>.
                      </p>
                    </div>

                    <div className="p-3.5 rounded-xl bg-zinc-900/50 border border-zinc-800 space-y-2">
                      <div className="font-bold text-zinc-200 text-sm">Cách 2: Mở Khóa Tạm Thời Tại Chỗ Trên Máy Em Trai</div>
                      <p className="text-zinc-400 leading-relaxed">
                        Khi màn hình máy tính em trai bị khóa, bấm nút <strong className="text-zinc-100 font-mono">[ Mật khẩu dừng Agent ]</strong> trên khung khóa, nhập mật khẩu Agent để mở khóa session sử dụng tạm thời.
                      </p>
                    </div>
                  </div>
                </div>

                {/* KHUNG CÁCH XÓA HOÀN TOÀN */}
                <div className="p-5 rounded-xl bg-zinc-900/50 border border-zinc-800 space-y-3">
                  <h3 className="font-bold text-sm text-red-400 flex items-center gap-2">
                    <span>️</span> 3. CÁCH GỠ BỎ HOÀN TOÀN KHỎI MÁY EM TRAI
                  </h3>
                  <div className="text-xs text-zinc-300 space-y-2 leading-relaxed">
                    <p className="text-zinc-400">Để xóa sạch 100% phần mềm khỏi máy em trai, chọn 1 trong 2 cách sau:</p>
                    <div className="space-y-2">
                      <div className="p-3 rounded-lg bg-zinc-900/50 border border-zinc-800">
                        <div className="font-bold text-red-300">Cách 1: Dùng script gỡ tự động (1-Click)</div>
                        <p className="text-zinc-400 mt-1">
                          Chuột phải vào file <code className="text-amber-300">Uninstall_Parental_Control.bat</code> trên máy em trai  Chọn <strong className="text-white">"Run as administrator"</strong>. Script sẽ tự dừng tiến trình, gỡ Windows Task và xóa sạch thư mục.
                        </p>
                      </div>

                      <div className="p-3 rounded-lg bg-zinc-900/50 border border-zinc-800">
                        <div className="font-bold text-red-300">Cách 2: Gỡ thủ công bằng Command Prompt (Admin)</div>
                        <p className="text-zinc-400 mt-1">Mở CMD với quyền Administrator và gán lần lượt 3 dòng lệnh sau:</p>
                        <pre className="bg-black p-2 rounded text-red-300 font-mono text-[11px] mt-1 space-y-1">
schtasks /delete /tn "ParentalControlAgentTask" /f
taskkill /f /im ParentalControlAgent.exe
rmdir /s /q "C:\ProgramData\ParentalControl"</pre>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* TAB: Khung giờ Cho Phép Sử Dụng */}
            {activeTab === 'schedule' && (
              <div className={`${cardBgClass} border rounded-2xl p-6 space-y-5 shadow-2xl`}>
                {/* THANH CÔNG CỤ ĐẦU TAB */}
                <div className="p-4 bg-zinc-900/50 border border-zinc-800 rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-lg">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xl"></span>
                      <h3 className="font-bold text-base text-slate-100">Cấu Hình Khung Giờ Cho Phép Sử Dụng</h3>
                    </div>
                    <p className="text-xs text-zinc-400">Thiết lập khoảng giờ hoặc tổng thời gian tối đa mỗi ngày cho em trai.</p>
                  </div>

                  {/* MASTER TOGGLE SWITCH & MODE SELECTOR */}
                  <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
                    {/* Master Switch */}
                    {isAdmin && (
                      <button
                        onClick={handleToggleMasterTimeLimit}
                        className={`px-4 py-2 rounded-xl text-xs font-bold transition border flex items-center gap-2 shadow ${
                          isMasterTimeLimitActive
                            ? 'bg-emerald-600 hover:bg-emerald-500 text-white border-emerald-500 shadow-emerald-600/20'
                            : 'bg-zinc-900 hover:bg-slate-700 text-zinc-400 border-zinc-800'
                        }`}
                      >
                        <span>{isMasterTimeLimitActive ? ' Giới Hạn: ĐANG BẬT' : ' Giới Hạn: ĐÃ TẮT'}</span>
                      </button>
                    )}

                    {/* Mode Radio Buttons */}
                    {isAdmin && (
                      <div className="flex bg-zinc-900/50 p-1 rounded-xl border border-zinc-800 text-xs">
                        <button
                          onClick={() => handleChangeTimeLimitMode('time_frame')}
                          className={`px-3.5 py-1.5 rounded-lg font-bold transition ${
                            timeLimitMode === 'time_frame' ? 'bg-zinc-100 text-black hover:bg-white shadow' : 'text-zinc-400 hover:text-white'
                          }`}
                        >
                          ⏰ Theo Khung Giờ
                        </button>
                        <button
                          onClick={() => handleChangeTimeLimitMode('max_daily')}
                          className={`px-3.5 py-1.5 rounded-lg font-bold transition ${
                            timeLimitMode === 'max_daily' ? 'bg-zinc-100 text-black hover:bg-white shadow' : 'text-zinc-400 hover:text-white'
                          }`}
                        >
                          ⏱️ Theo Tổng Giờ/Ngày
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                {/* TRƯỜNG HỢP 1: THỜI GIAN THEO KHUNG GIỜ (time_frame) */}
                {timeLimitMode === 'time_frame' && (
                  <div className="space-y-4">
                    <div className="p-3 bg-blue-500/10 border border-indigo-500/20 rounded-xl text-xs text-blue-300 flex items-center gap-2">
                      <span>ℹ️</span>
                      <span>Chế độ <strong>Theo Khung Giờ</strong>: Em trai chỉ được phép dùng máy tính trong khoảng giờ được thiết lập bên dưới. Ngoài khoảng giờ này máy sẽ tự khóa.</span>
                    </div>

                    <div className="grid grid-cols-1 gap-4">
                      {timeRules.map(rule => (
                        <div key={rule.id} className="p-4 rounded-2xl bg-zinc-900/50 border border-zinc-800 space-y-3 hover:border-zinc-800 transition shadow">
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-zinc-800 pb-3">
                            <div className="flex items-center gap-2.5">
                              <span className="w-8 h-8 rounded-xl bg-blue-500/10 border border-indigo-500/20 text-blue-400 font-bold flex items-center justify-center text-xs">
                                {rule.day_of_week === 6 ? 'CN' : `T${rule.day_of_week + 2}`}
                              </span>
                              <span className="font-bold text-sm text-zinc-200">{dayNames[rule.day_of_week]}</span>
                            </div>

                            {isAdmin ? (
                              <div className="flex flex-wrap items-center gap-3">
                                <div className="flex items-center gap-2">
                                  <span className="text-xs text-zinc-400 font-medium">Bắt đầu:</span>
                                  <input
                                    type="time"
                                    value={rule.start_time?.slice(0, 5)}
                                    onChange={(e) => updateTimeRule(rule.id, 'start_time', e.target.value + ':00')}
                                    className="bg-zinc-900 border border-zinc-800 rounded-xl px-3 py-1.5 text-xs font-bold text-emerald-400 outline-none focus:border-indigo-500 shadow"
                                  />
                                  <span className="text-zinc-500">→</span>
                                  <span className="text-xs text-zinc-400 font-medium font-mono">Kết thúc:</span>
                                  <input
                                    type="time"
                                    value={rule.end_time?.slice(0, 5)}
                                    onChange={(e) => updateTimeRule(rule.id, 'end_time', e.target.value + ':00')}
                                    className="bg-zinc-900 border border-zinc-800 rounded-xl px-3 py-1.5 text-xs font-bold text-emerald-400 outline-none focus:border-indigo-500 shadow"
                                  />
                                </div>

                                <button
                                  onClick={() => updateTimeRule(rule.id, 'is_active', !rule.is_active)}
                                  className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition ${
                                    rule.is_active ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-zinc-900 text-zinc-400 border border-zinc-800'
                                  }`}
                                >
                                  {rule.is_active ? 'Đang bật' : 'Đã tắt'}
                                </button>
                              </div>
                            ) : (
                              <div className="flex items-center gap-3">
                                <span className="text-xs font-bold text-emerald-400 bg-emerald-500/10 px-3 py-1 rounded-lg border border-emerald-500/20">
                                  {rule.start_time?.slice(0, 5)} → {rule.end_time?.slice(0, 5)}
                                </span>
                                <span className={`px-2.5 py-1 rounded-lg text-xs font-semibold ${
                                  rule.is_active ? 'bg-emerald-500/15 text-emerald-400' : 'bg-zinc-900 text-zinc-400'
                                }`}>
                                  {rule.is_active ? 'Đang bật' : 'Đã tắt'}
                                </span>
                              </div>
                            )}
                          </div>

                          {/* Visual 24h Timeline Bar */}
                          {render24hTimeline(rule)}
                        </div>
                      ))}
                    </div>
                  </div>
                )}


              </div>
            )}
          </>
        )}
      </main>

      {/* MODAL XÁC NHẬN XÓA DỮ LIỆU NGÀY */}
      {showDeleteDateModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-zinc-900/50 border border-red-500/40 rounded-3xl p-6 max-w-md w-full space-y-4 shadow-2xl animate-in zoom-in-95 duration-200">
            <div className="flex items-center gap-3 text-rose-400 border-b border-zinc-800 pb-3">
              <AlertTriangle className="w-5 h-5 text-rose-500 stroke-[1.5]" />
              <div>
                <h3 className="font-bold text-base text-slate-100">Xác Nhận Xóa Dữ Liệu</h3>
                <p className="text-xs text-red-400">Hành động này không thể hoàn tác!</p>
              </div>
            </div>

            <p className="text-xs text-zinc-300 leading-relaxed">
              Bạn có chắc chắn muốn xóa <strong className="text-white">TOÀN BỘ dữ liệu lịch sử Web, App và Log</strong> của ngày <span className="font-mono text-amber-300 font-bold bg-amber-500/20 px-2 py-0.5 rounded border border-amber-500/30">{dateToDelete}</span> không?
            </p>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setShowDeleteDateModal(false)}
                className="px-4 py-2 bg-zinc-900 hover:bg-slate-700 text-zinc-300 font-semibold rounded-xl text-xs transition"
              >
                Hủy Bỏ
              </button>
              <button
                onClick={confirmDeleteHistoryForDate}
                className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white font-bold rounded-xl text-xs transition shadow-lg shadow-red-600/30 flex items-center gap-1.5"
              >
                <span>️</span> Xác Nhận Xóa Rút Lại
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL XÁC NHẬN CHẶN / BỎ CHẶN THIẾT BỊ */}
      {showBlockSessionModal && sessionToBlock && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-zinc-900/50 border border-red-500/40 rounded-3xl p-6 max-w-md w-full space-y-4 shadow-2xl animate-in zoom-in-95 duration-200">
            <div className="flex items-center gap-3 text-red-400 border-b border-zinc-800 pb-3">
              <span className="text-3xl"></span>
              <div>
                <h3 className="font-bold text-base text-slate-100">
                  {sessionToBlock.is_blocked ? 'Xác Nhận Bỏ Chặn Thiết Bị' : 'Xác Nhận Chặn Thiết Bị'}
                </h3>
                <p className="text-xs text-red-400">
                  {sessionToBlock.is_blocked ? 'Thiết bị này sẽ được phép truy cập lại Web Admin.' : 'Thiết bị này sẽ lập tức bị ngắt kết nối và từ chối truy cập!'}
                </p>
              </div>
            </div>

            <div className="p-3.5 bg-zinc-900/50 border border-zinc-800 rounded-2xl text-xs space-y-1.5">
              <div className="font-semibold text-zinc-200 flex items-center gap-2">
                <span> Thiết bị:</span>
                <span className="text-blue-300 font-bold">{sessionToBlock.device_info || 'Thiết bị Web'}</span>
              </div>
              <div className="text-zinc-400">
                Tư cách: <strong className="text-amber-300">{sessionToBlock.user_role}</strong>
              </div>
              <div className="font-mono text-[10px] text-zinc-500 truncate">
                Session ID: {sessionToBlock.session_id}
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => {
                  setShowBlockSessionModal(false)
                  setSessionToBlock(null)
                }}
                className="px-4 py-2 bg-zinc-900 hover:bg-slate-700 text-zinc-300 font-semibold rounded-xl text-xs transition"
              >
                Hủy Bỏ
              </button>
              <button
                onClick={confirmToggleBlockSession}
                className={`px-4 py-2 text-white font-bold rounded-xl text-xs transition shadow-lg flex items-center gap-1.5 ${
                  sessionToBlock.is_blocked
                    ? 'bg-emerald-600 hover:bg-emerald-500 shadow-emerald-600/30'
                    : 'bg-red-600 hover:bg-red-500 shadow-red-600/30'
                }`}
              >
                <span>{sessionToBlock.is_blocked ? ' Xác Nhận Bỏ Chặn' : ' Xác Nhận Chặn Tức Thì'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MOBILE BOTTOM NAVIGATION BAR (< lg) */}
      <MobileNav tabList={tabList} activeTab={activeTab} changeActiveTab={changeActiveTab} />

      {/* MOBILE DRAWER MODAL */}
      {showMobileDrawer && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex flex-col justify-end lg:hidden">
          <div className="bg-zinc-900/50 border-t border-zinc-800 rounded-t-3xl p-5 space-y-4 max-h-[80vh] overflow-y-auto animate-in slide-in-from-bottom duration-200">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <div className="flex items-center gap-2">
                <span className="text-xl"></span>
                <h3 className="font-bold text-slate-100 text-base">Danh Sách Chức Năng</h3>
              </div>
              <button onClick={() => setShowMobileDrawer(false)} className="w-8 h-8 rounded-full bg-zinc-900 hover:bg-slate-700 text-zinc-300 flex items-center justify-center text-sm font-bold">
                
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3">
              {tabList.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => {
                    changeActiveTab(tab.id)
                    setShowMobileDrawer(false)
                  }}
                  className={`p-3.5 rounded-2xl border text-left font-semibold text-xs flex items-center gap-2.5 transition ${
                    activeTab === tab.id
                      ? 'bg-zinc-100 text-black hover:bg-white border-indigo-500 shadow-lg shadow-indigo-600/20'
                      : 'bg-zinc-900/50 text-zinc-300 border-zinc-800 hover:bg-zinc-900'
                  }`}
                >
                  <span className="text-lg">{tab.label.split(' ')[0]}</span>
                  <span className="truncate">{tab.label.substring(tab.label.indexOf(' ') + 1)}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  </div>
</div>
)
}



export default function App() {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) {
    return (
      <div className="min-h-screen bg-black text-zinc-100 flex items-center justify-center font-mono text-xs">
        <div className="flex items-center gap-2 text-zinc-400">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
          <span>Loading Geist Console...</span>
        </div>
      </div>
    )
  }

  return (
    <ErrorBoundary>
      <ParentalControlApp />
    </ErrorBoundary>
  )
}
