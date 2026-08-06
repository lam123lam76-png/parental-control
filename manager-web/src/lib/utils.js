// manager-web/src/lib/utils.js
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

// Helper parse date string into { day, month, year }
export function parseSheetDateStr(dateStr) {
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

export function isSameDateParsed(d1, d2) {
  if (!d1 || !d2) return false
  return d1.day === d2.day && d1.month === d2.month && d1.year === d2.year
}

// Google Sheet Parsing với Forward Fill cho Cột Buổi gộp & Strict Row Filtering
export function parseGoogleSheetData(csvText) {
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

    // Cột C: Khung giờ / Buổi (Forward Fill cho ô gộp)
    const rawSessionCell = row[sessionColIdx] ? row[sessionColIdx].trim() : ''
    if (rawSessionCell && rawSessionCell !== '-' && !rawSessionCell.toUpperCase().includes('KHUNG GIỜ')) {
      currentSession = rawSessionCell
    }

    // Cột D: THỜI GIAN & Cột E: NỘI DUNG CÔNG VIỆC
    const rawTime = row[timeColIdx] ? row[timeColIdx].trim() : ''
    const rawContent = row[contentColIdx] ? row[contentColIdx].trim() : ''
    const rawPriority = row[priorityColIdx] ? row[priorityColIdx].trim() : ''

    const cleanTime = rawTime.replace(/\s+/g, ' ').trim()
    const cleanContent = rawContent.replace(/\s+/g, ' ').trim()
    const sessionName = currentSession ? (currentSession.charAt(0).toUpperCase() + currentSession.slice(1)) : ''

    // 2. Strict Task Filtering (Skip dòng rỗng, ?h ~?h, tiêu đề gộp 1h-2h, 11h-8h, theo gia đình)
    const skipKeywords = ['1h-2h', '11h-8h', 'theo gia đình', '?h ~?h', 'nội dung công việc']
    const contentLower = cleanContent.toLowerCase()

    if (
      !cleanTime ||
      cleanTime === '-' ||
      cleanTime.includes('?h ~?h') ||
      !cleanContent ||
      cleanContent === '-' ||
      cleanContent.length <= 2 ||
      skipKeywords.some(kw => contentLower.includes(kw))
    ) {
      continue
    }

    // 3. Priority Tag Mapping
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
    }

    let formattedSessionTime = sessionName
    if (cleanTime && cleanTime !== '-' && cleanTime !== '?h ~?h') {
      formattedSessionTime = sessionName ? `${sessionName} (${cleanTime})` : cleanTime
    }
    if (!formattedSessionTime) formattedSessionTime = 'Cả ngày'

    const parsedRowDate = parseSheetDateStr(rawDate)
    const isExactToday = isSameDateParsed(parsedRowDate, todayObj)

    allEntries.push({
      id: `sheet_${i}`,
      date: rawDate || `${todayObj.day}/${todayObj.month}/${todayObj.year}`,
      session: currentSession || 'sáng',
      time: cleanTime,
      title: cleanContent,
      content: cleanContent,
      priority: priorityCode,
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
    const key = `${item.title.toLowerCase()}_${item.time.toLowerCase()}`
    if (!seen.has(key)) {
      seen.add(key)
      deduplicatedToday.push(item)
    }
  }

  deduplicatedToday.sort((a, b) => b.priorityScore - a.priorityScore)
  return { allEntries, todayEntries: deduplicatedToday }
}

// Group & Deduplicate active sessions by unique device_id
export function deduplicateActiveSessions(sessions) {
  if (!Array.isArray(sessions)) return []
  const seen = new Set()
  const result = []
  for (const s of sessions) {
    const devId = s.device_id || s.id
    if (devId && !seen.has(devId)) {
      seen.add(devId)
      result.push(s)
    }
  }
  return result
}

// Time Format Helpers
export function formatClockTime(isoStr) {
  if (!isoStr) return ''
  try {
    const d = new Date(isoStr)
    return d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch (e) {
    return ''
  }
}

// ================================================================
// 🔥 HÀM CN CHO SHADCN/UI (THÊM MỚI)
// ================================================================

/**
 * Hàm gộp class names với Tailwind CSS
 * Sử dụng clsx để xử lý conditional classes và tailwind-merge để tránh xung đột
 */
export function cn(...inputs) {
  return twMerge(clsx(inputs))
}