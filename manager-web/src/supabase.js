const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || ''
const apiKey = import.meta.env.VITE_API_KEY || ''

class TableQuery {
  constructor(client, table) {
    this.client = client
    this.table = table
    this.operation = 'select'
    this.selectColumns = '*'
    this.filters = []
    this.orderBy = []
    this.limitValue = undefined
    this.data = undefined
    this.onConflict = undefined
    this.maybeSingleValue = false
  }

  select(columns = '*') {
    this.operation = 'select'
    this.selectColumns = columns
    return this
  }

  insert(data) {
    this.operation = 'insert'
    this.data = data
    return this
  }

  upsert(data, { onConflict } = {}) {
    this.operation = 'upsert'
    this.data = data
    this.onConflict = onConflict
    return this
  }

  update(data) {
    this.operation = 'update'
    this.data = data
    return this
  }

  delete() {
    this.operation = 'delete'
    return this
  }

  eq(column, value) {
    this.filters.push({ op: 'eq', column, value })
    return this
  }

  neq(column, value) {
    this.filters.push({ op: 'neq', column, value })
    return this
  }

  lt(column, value) {
    this.filters.push({ op: 'lt', column, value })
    return this
  }

  lte(column, value) {
    this.filters.push({ op: 'lte', column, value })
    return this
  }

  gt(column, value) {
    this.filters.push({ op: 'gt', column, value })
    return this
  }

  gte(column, value) {
    this.filters.push({ op: 'gte', column, value })
    return this
  }

  in(column, values) {
    this.filters.push({ op: 'in', column, value: values })
    return this
  }

  order(column, options = {}) {
    const ascending = typeof options === 'boolean' ? options : options?.ascending !== false
    this.orderBy.push({ column, ascending })
    return this
  }

  limit(value) {
    this.limitValue = value
    return this
  }

  maybeSingle() {
    this.maybeSingleValue = true
    return this
  }

  single() {
    return this.maybeSingle()
  }

  async execute() {
    return this.client._executeQuery(this)
  }

  then(resolve, reject) {
    return this.execute().then(resolve, reject)
  }
}

class StorageBucket {
  constructor(client, bucket) {
    this.client = client
    this.bucket = bucket
  }

  async remove(paths) {
    const body = { paths: Array.isArray(paths) ? paths : [paths] }
    return this.client._request(`/api/storage/${this.bucket}/remove`, 'POST', body)
  }

  getPublicUrl(path) {
    const normalizedPath = encodeURI(path)
    const prefix = apiBaseUrl.replace(/\/$/, '')
    const publicUrl = prefix ? `${prefix}/storage/${this.bucket}/${normalizedPath}` : `/storage/${this.bucket}/${normalizedPath}`
    return { data: { publicUrl }, error: null }
  }

  async upload({ path, file, fileOptions } = {}) {
    const formData = new FormData()
    formData.append('path', path)
    formData.append('file', file)
    const headers = this.client._authHeaders(false)
    const response = await fetch(`${this.client.baseUrl || ''}/api/storage/${this.bucket}/upload`, {
      method: 'POST',
      headers,
      body: formData,
    })
    return this.client._parseResponse(response)
  }
}

class StorageClient {
  constructor(client) {
    this.client = client
  }

  from(bucket) {
    return new StorageBucket(this.client, bucket)
  }
}

class SupabaseClient {
  constructor(baseUrl, apiKey) {
    this.baseUrl = baseUrl.replace(/\/$/, '')
    this.apiKey = apiKey
    this.storage = new StorageClient(this)
  }

  from(table) {
    return new TableQuery(this, table)
  }

  rpc(procedure, params = {}) {
    return this._request(`/api/rpc/${procedure}`, 'POST', { params })
  }

  _authHeaders(json = true) {
    const headers = {}
    if (this.apiKey) {
      headers.Authorization = `Bearer ${this.apiKey}`
    }
    if (json) {
      headers['Content-Type'] = 'application/json'
    }
    return headers
  }

  async _request(path, method, body) {
    const response = await fetch(`${this.baseUrl || ''}${path}`, {
      method,
      headers: this._authHeaders(),
      body: body ? JSON.stringify(body) : undefined,
    })
    return this._parseResponse(response)
  }

  async _parseResponse(response) {
    let payload = null
    try {
      payload = await response.json()
    } catch (error) {
      return { data: null, error: `Invalid JSON response: ${error}` }
    }
    if (!response.ok) {
      return { data: null, error: payload?.detail || payload?.error || `HTTP ${response.status}` }
    }
    return { data: payload.data, error: payload.error || null }
  }

  async _executeQuery(query) {
    return this._request('/api/query', 'POST', {
      table: query.table,
      operation: query.operation,
      select: query.selectColumns,
      filters: query.filters,
      order: query.orderBy,
      limit: query.limitValue,
      maybe_single: query.maybeSingleValue,
      on_conflict: query.onConflict,
      data: query.data,
    })
  }
}

export const supabase = new SupabaseClient(apiBaseUrl, apiKey)


