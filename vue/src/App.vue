<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { getRecommend, getExperiments, getMetrics, healthCheck, connectVectorStore, upsertProducts, getVectorStats } from './api/index.js'

// State
const loading = ref(false)
const result = ref(null)
const experiments = ref(null)
const metrics = ref(null)
const health = ref(null)
const activeTab = ref('recommend')
const connectionStatus = ref('checking')

// Vector Store State
const vectorStats = ref(null)
const vectorConnecting = ref(false)
const vectorUpserting = ref(false)

// Form data
const formData = ref({
  user_id: 'user_001',
  scene: 'homepage',
  num_items: 5,
  context: {
    recent_views: ['手机', '耳机'],
    avg_order_amount: 500,
    last_purchase_days: 7
  }
})

// Scene options
const scenes = [
  { value: 'homepage', label: '首页推荐' },
  { value: 'product_detail', label: '商品详情' },
  { value: 'cart', label: '购物车' },
  { value: 'search', label: '搜索结果' }
]

// Check health periodically
let healthInterval
const checkHealth = async () => {
  try {
    const res = await healthCheck()
    health.value = res
    connectionStatus.value = 'connected'
  } catch (e) {
    connectionStatus.value = 'disconnected'
  }
}

// Get recommendation
const fetchRecommend = async () => {
  loading.value = true
  try {
    const res = await getRecommend(formData.value)
    result.value = res
  } catch (e) {
    console.error('Recommend error:', e)
    result.value = { error: e.message }
  } finally {
    loading.value = false
  }
}

// Get experiments
const fetchExperiments = async () => {
  try {
    experiments.value = await getExperiments()
  } catch (e) {
    console.error('Experiments error:', e)
  }
}

// Get metrics
const fetchMetrics = async () => {
  try {
    metrics.value = await getMetrics()
  } catch (e) {
    console.error('Metrics error:', e)
  }
}

// Refresh all data
const refreshAll = async () => {
  await Promise.all([fetchExperiments(), fetchMetrics(), fetchVectorStats()])
}

// ==================== Vector Store ====================

// Get vector store stats
const fetchVectorStats = async () => {
  try {
    vectorStats.value = await getVectorStats()
  } catch (e) {
    console.error('Vector stats error:', e)
    vectorStats.value = null
  }
}

// Connect to vector store
const handleConnectVector = async () => {
  vectorConnecting.value = true
  try {
    const res = await connectVectorStore()
    vectorStats.value = res.stats
  } catch (e) {
    console.error('Connect vector error:', e)
  } finally {
    vectorConnecting.value = false
  }
}

// Upsert products to vector store
const handleUpsertProducts = async () => {
  vectorUpserting.value = true
  try {
    await upsertProducts()
    await fetchVectorStats()
  } catch (e) {
    console.error('Upsert products error:', e)
  } finally {
    vectorUpserting.value = false
  }
}

// Format latency
const formatLatency = (ms) => {
  if (!ms) return '--'
  return `${ms.toFixed(1)}ms`
}

// Get status color
const getStatusColor = (status) => {
  return status === 'connected' ? 'var(--accent-green)' : 'var(--accent-orange)'
}

onMounted(() => {
  checkHealth()
  healthInterval = setInterval(checkHealth, 5000)
  fetchExperiments()
  fetchMetrics()
})

onUnmounted(() => {
  if (healthInterval) clearInterval(healthInterval)
})
</script>

<template>
  <div class="app-container">
    <!-- Header -->
    <header class="header">
      <div class="header-content">
        <div class="logo-section">
          <div class="logo-icon">
            <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="20" cy="20" r="18" stroke="url(#grad1)" stroke-width="2" fill="none"/>
              <circle cx="20" cy="12" r="4" fill="#22d3ee"/>
              <circle cx="12" cy="26" r="4" fill="#a855f7"/>
              <circle cx="28" cy="26" r="4" fill="#ec4899"/>
              <line x1="20" y1="16" x2="14" y2="22" stroke="#22d3ee" stroke-width="1.5"/>
              <line x1="20" y1="16" x2="26" y2="22" stroke="#22d3ee" stroke-width="1.5"/>
              <line x1="16" y1="26" x2="24" y2="26" stroke="#a855f7" stroke-width="1.5" stroke-dasharray="2 2"/>
              <defs>
                <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="#22d3ee"/>
                  <stop offset="50%" stop-color="#a855f7"/>
                  <stop offset="100%" stop-color="#ec4899"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
          <div class="logo-text">
            <h1 class="title">Multi-Agent</h1>
            <span class="subtitle">E-Commerce Recommendation System</span>
          </div>
        </div>
        
        <div class="header-right">
          <div class="status-indicator" :style="{ '--status-color': getStatusColor(connectionStatus) }">
            <span class="status-dot"></span>
            <span class="status-text">{{ connectionStatus === 'connected' ? '已连接' : '未连接' }}</span>
          </div>
          <div class="model-badge" v-if="health">
            <span class="model-label">Model</span>
            <span class="model-name">{{ health.model }}</span>
          </div>
        </div>
      </div>
      
      <!-- Navigation Tabs -->
      <nav class="nav-tabs">
        <button 
          v-for="tab in ['recommend', 'experiments', 'vector', 'metrics']" 
          :key="tab"
          :class="['nav-tab', { active: activeTab === tab }]"
          @click="activeTab = tab"
        >
          <span class="tab-icon">
            <template v-if="tab === 'recommend'">⟡</template>
            <template v-else-if="tab === 'experiments'">⬡</template>
            <template v-else-if="tab === 'vector'">◈</template>
            <template v-else>◇</template>
          </span>
          <span class="tab-label">
            {{ tab === 'recommend' ? '智能推荐' : tab === 'experiments' ? 'A/B 实验' : tab === 'vector' ? '向量存储' : '系统监控' }}
          </span>
        </button>
      </nav>
    </header>

    <!-- Main Content -->
    <main class="main-content">
      <!-- Recommend Tab -->
      <section v-show="activeTab === 'recommend'" class="panel recommend-panel">
        <div class="panel-grid">
          <!-- Input Form -->
          <div class="card form-card">
            <div class="card-header">
              <h2 class="card-title">推荐请求</h2>
              <span class="card-badge">POST /api/v1/recommend</span>
            </div>
            
            <form @submit.prevent="fetchRecommend" class="form">
              <div class="form-row">
                <label class="form-label">
                  <span class="label-text">用户 ID</span>
                  <input 
                    v-model="formData.user_id" 
                    type="text" 
                    class="form-input"
                    placeholder="user_001"
                  >
                </label>
                
                <label class="form-label">
                  <span class="label-text">推荐场景</span>
                  <select v-model="formData.scene" class="form-select">
                    <option v-for="s in scenes" :key="s.value" :value="s.value">
                      {{ s.label }}
                    </option>
                  </select>
                </label>
              </div>
              
              <div class="form-row">
                <label class="form-label">
                  <span class="label-text">推荐数量</span>
                  <input 
                    v-model.number="formData.num_items" 
                    type="number" 
                    min="1" 
                    max="20"
                    class="form-input"
                  >
                </label>
              </div>
              
              <div class="form-section">
                <h3 class="section-title">用户上下文</h3>
                <div class="form-row">
                  <label class="form-label flex-1">
                    <span class="label-text">最近浏览 (逗号分隔)</span>
                    <input 
                      :value="formData.context.recent_views.join(', ')"
                      @input="formData.context.recent_views = $event.target.value.split(',').map(s => s.trim()).filter(Boolean)"
                      type="text" 
                      class="form-input"
                      placeholder="手机, 耳机, 充电宝"
                    >
                  </label>
                </div>
                <div class="form-row">
                  <label class="form-label">
                    <span class="label-text">平均订单金额</span>
                    <input 
                      v-model.number="formData.context.avg_order_amount" 
                      type="number" 
                      class="form-input"
                    >
                  </label>
                  <label class="form-label">
                    <span class="label-text">距上次购买(天)</span>
                    <input 
                      v-model.number="formData.context.last_purchase_days" 
                      type="number" 
                      class="form-input"
                    >
                  </label>
                </div>
              </div>
              
              <button type="submit" class="btn-primary" :disabled="loading">
                <span v-if="loading" class="loading-spinner"></span>
                <span v-else class="btn-icon">▶</span>
                <span>{{ loading ? '请求中...' : '发送请求' }}</span>
              </button>
            </form>
          </div>
          
          <!-- Results Panel -->
          <div class="card result-card">
            <div class="card-header">
              <h2 class="card-title">推荐结果</h2>
              <span v-if="result?.total_latency_ms" class="latency-badge">
                {{ formatLatency(result.total_latency_ms) }}
              </span>
            </div>
            
            <div v-if="!result" class="result-empty">
              <div class="empty-icon">◯</div>
              <p>等待请求...</p>
            </div>
            
            <div v-else-if="result.error" class="result-error">
              <span class="error-icon">⚠</span>
              <span>{{ result.error }}</span>
            </div>
            
            <div v-else class="result-content">
              <!-- Meta Info -->
              <div class="result-meta">
                <div class="meta-item">
                  <span class="meta-label">Request ID</span>
                  <span class="meta-value text-mono">{{ result.request_id?.slice(0, 8) }}...</span>
                </div>
                <div class="meta-item">
                  <span class="meta-label">实验分组</span>
                  <span class="meta-value experiment-group">{{ result.experiment_group }}</span>
                </div>
              </div>
              
              <!-- Products -->
              <div class="products-section">
                <h3 class="section-title">推荐商品 ({{ result.products?.length || 0 }})</h3>
                <div class="products-grid">
                  <div 
                    v-for="(product, idx) in result.products" 
                    :key="product.product_id"
                    class="product-card"
                    :style="{ '--delay': idx * 0.1 + 's' }"
                  >
                    <div class="product-rank">{{ idx + 1 }}</div>
                    <div class="product-info">
                      <span class="product-id text-mono">{{ product.product_id }}</span>
                      <span class="product-name">{{ product.name }}</span>
                      <div class="product-meta">
                        <span class="product-category">{{ product.category }}</span>
                        <span class="product-price">¥{{ product.price?.toLocaleString() }}</span>
                      </div>
                    </div>
                    <div class="product-score">
                      <span class="score-value">{{ (product.score * 100).toFixed(0) }}</span>
                      <span class="score-label">score</span>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- Marketing Copies -->
              <div v-if="result.marketing_copies?.length" class="copies-section">
                <h3 class="section-title">营销文案</h3>
                <div class="copies-list">
                  <div 
                    v-for="copy in result.marketing_copies" 
                    :key="copy.product_id"
                    class="copy-item"
                  >
                    <span class="copy-product text-mono">{{ copy.product_id }}</span>
                    <p class="copy-text">{{ copy.copy }}</p>
                  </div>
                </div>
              </div>
              
              <!-- Agent Results -->
              <div v-if="result.agent_results" class="agents-section">
                <h3 class="section-title">Agent 执行详情</h3>
                <div class="agents-grid">
                  <div 
                    v-for="(agent, name) in result.agent_results" 
                    :key="name"
                    class="agent-item"
                  >
                    <span class="agent-name">{{ name }}</span>
                    <span :class="['agent-status', agent.success ? 'success' : 'failed']">
                      {{ agent.success ? '✓' : '✗' }}
                    </span>
                    <span class="agent-latency">{{ formatLatency(agent.latency_ms) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Experiments Tab -->
      <section v-show="activeTab === 'experiments'" class="panel experiments-panel">
        <div class="panel-header">
          <h2 class="panel-title">A/B 实验监控</h2>
          <button @click="fetchExperiments" class="btn-refresh">↻ 刷新</button>
        </div>
        
        <div v-if="!experiments" class="loading-state">
          <span class="loading-spinner large"></span>
          <span>加载中...</span>
        </div>
        
        <div v-else class="experiments-grid">
          <div 
            v-for="(exp, expId) in experiments" 
            :key="expId"
            class="experiment-card"
          >
            <div class="exp-header">
              <h3 class="exp-name">{{ exp.name }}</h3>
              <span :class="['exp-status', exp.enabled ? 'enabled' : 'disabled']">
                {{ exp.enabled ? '启用' : '禁用' }}
              </span>
            </div>
            
            <div class="exp-groups">
              <div 
                v-for="group in exp.groups" 
                :key="group.name"
                class="group-item"
              >
                <div class="group-header">
                  <span class="group-name">{{ group.name }}</span>
                  <span class="group-weight">{{ (group.weight * 100).toFixed(0) }}%</span>
                </div>
                <div class="group-bar">
                  <div class="bar-fill" :style="{ width: group.weight * 100 + '%' }"></div>
                </div>
                <div class="group-stats">
                  <span class="stat">✓ {{ group.successes }}</span>
                  <span class="stat">✗ {{ group.failures }}</span>
                </div>
              </div>
            </div>
            
            <div v-if="exp.stats" class="exp-stats">
              <div class="stat-item">
                <span class="stat-label">Total Samples</span>
                <span class="stat-value">{{ exp.stats.total_samples }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">Success Rate</span>
                <span class="stat-value">{{ (exp.stats.success_rate * 100).toFixed(1) }}%</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Vector Store Tab -->
      <section v-show="activeTab === 'vector'" class="panel vector-panel">
        <div class="panel-header">
          <h2 class="panel-title">向量存储管理</h2>
          <button @click="fetchVectorStats" class="btn-refresh">↻ 刷新</button>
        </div>

        <div class="vector-grid">
          <!-- Connection Card -->
          <div class="card connection-card">
            <div class="card-header">
              <h3 class="card-title">Milvus 连接</h3>
              <span :class="['status-badge', vectorStats?.connected ? 'connected' : 'disconnected']">
                {{ vectorStats?.connected ? '已连接' : '未连接' }}
              </span>
            </div>

            <div class="connection-actions">
              <button 
                @click="handleConnectVector" 
                class="btn-action"
                :disabled="vectorConnecting"
              >
                <span v-if="vectorConnecting" class="loading-spinner"></span>
                <span v-else>⚡</span>
                <span>{{ vectorConnecting ? '连接中...' : '连接向量库' }}</span>
              </button>
            </div>
          </div>

          <!-- Stats Card -->
          <div class="card stats-card">
            <div class="card-header">
              <h3 class="card-title">存储统计</h3>
            </div>

            <div v-if="vectorStats" class="stats-content">
              <div class="stat-row">
                <span class="stat-label">Collection</span>
                <span class="stat-value text-mono">{{ vectorStats.collection || '--' }}</span>
              </div>
              <div class="stat-row">
                <span class="stat-label">向量数量</span>
                <span class="stat-value">{{ vectorStats.row_count?.toLocaleString() || 0 }}</span>
              </div>
              <div class="stat-row">
                <span class="stat-label">连接状态</span>
                <span :class="['stat-value', vectorStats.connected ? 'text-green' : 'text-orange']">
                  {{ vectorStats.connected ? '正常' : '断开' }}
                </span>
              </div>
            </div>
            <div v-else class="stats-empty">
              <span>暂无数据</span>
            </div>
          </div>

          <!-- Data Sync Card -->
          <div class="card sync-card">
            <div class="card-header">
              <h3 class="card-title">数据同步</h3>
            </div>

            <p class="sync-desc">将 Mock 商品数据写入 Milvus 向量数据库，用于向量检索推荐。</p>

            <div class="sync-actions">
              <button 
                @click="handleUpsertProducts" 
                class="btn-action primary"
                :disabled="vectorUpserting || !vectorStats?.connected"
              >
                <span v-if="vectorUpserting" class="loading-spinner"></span>
                <span v-else>📤</span>
                <span>{{ vectorUpserting ? '同步中...' : '同步商品数据' }}</span>
              </button>
            </div>
          </div>

          <!-- Info Card -->
          <div class="card info-card">
            <div class="card-header">
              <h3 class="card-title">使用说明</h3>
            </div>

            <ul class="info-list">
              <li>向量数据库使用 <strong>Milvus</strong>，嵌入模型使用 <strong>Ollama nomic-embed-text</strong></li>
              <li>首次使用需先连接向量库，再同步商品数据</li>
              <li>推荐请求会自动使用向量检索（如已连接），否则降级到 Mock 数据</li>
              <li>Docker 环境需确保 Milvus 和 Ollama 服务正常运行</li>
            </ul>
          </div>
        </div>
      </section>

      <!-- Metrics Tab -->
      <section v-show="activeTab === 'metrics'" class="panel metrics-panel">
        <div class="panel-header">
          <h2 class="panel-title">系统监控指标</h2>
          <button @click="fetchMetrics" class="btn-refresh">↻ 刷新</button>
        </div>
        
        <div v-if="!metrics" class="loading-state">
          <span class="loading-spinner large"></span>
          <span>加载中...</span>
        </div>
        
        <div v-else class="metrics-grid">
          <!-- Agent Stats -->
          <div class="metrics-card">
            <h3 class="metrics-title">Agent 调用统计</h3>
            <div class="metrics-table">
              <div class="table-header">
                <span>Agent</span>
                <span>Calls</span>
                <span>Success</span>
                <span>Avg Latency</span>
              </div>
              <div 
                v-for="(stat, name) in metrics.agents" 
                :key="name"
                class="table-row"
              >
                <span class="cell-name">{{ name }}</span>
                <span class="cell-value">{{ stat.total_calls }}</span>
                <span class="cell-value">{{ stat.success_calls }}</span>
                <span class="cell-value">{{ formatLatency(stat.avg_latency_ms) }}</span>
              </div>
            </div>
          </div>
          
          <!-- Business Stats -->
          <div class="metrics-card">
            <h3 class="metrics-title">业务指标</h3>
            <div class="business-stats">
              <div class="biz-stat">
                <span class="biz-value">{{ metrics.business?.total_requests || 0 }}</span>
                <span class="biz-label">总请求数</span>
              </div>
              <div class="biz-stat">
                <span class="biz-value">{{ metrics.business?.avg_latency_ms?.toFixed(1) || 0 }}ms</span>
                <span class="biz-label">平均延迟</span>
              </div>
              <div class="biz-stat">
                <span class="biz-value">{{ ((metrics.business?.success_rate || 0) * 100).toFixed(1) }}%</span>
                <span class="biz-label">成功率</span>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>

    <!-- Footer -->
    <footer class="footer">
      <div class="footer-content">
        <span class="footer-text">Multi-Agent E-Commerce System</span>
        <span class="footer-divider">|</span>
        <span class="footer-text text-mono">v1.0.0</span>
        <span class="footer-divider">|</span>
        <span class="footer-text">Powered by LangGraph + FastAPI</span>
      </div>
    </footer>
  </div>
</template>

<style scoped>
/* ===== App Container ===== */
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* ===== Header ===== */
.header {
  background: rgba(10, 14, 23, 0.9);
  border-bottom: 1px solid var(--border-primary);
  backdrop-filter: blur(20px);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.logo-icon {
  width: 40px;
  height: 40px;
  animation: float 3s ease-in-out infinite;
}

.logo-text {
  display: flex;
  flex-direction: column;
}

.title {
  font-size: 1.25rem;
  font-weight: 700;
  background: var(--gradient-cyber);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.subtitle {
  font-size: 0.75rem;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 20px;
  border: 1px solid var(--border-primary);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--status-color);
  animation: pulse-glow 2s ease-in-out infinite;
}

.status-text {
  font-size: 0.75rem;
  color: var(--text-secondary);
  font-family: var(--font-mono);
}

.model-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: rgba(139, 92, 246, 0.1);
  border: 1px solid rgba(139, 92, 246, 0.3);
  border-radius: 20px;
}

.model-label {
  font-size: 0.625rem;
  color: var(--accent-purple);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.model-name {
  font-size: 0.75rem;
  color: var(--text-primary);
  font-family: var(--font-mono);
}

/* ===== Navigation ===== */
.nav-tabs {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 2rem;
  display: flex;
  gap: 0.5rem;
}

.nav-tab {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-family: var(--font-display);
  font-size: 0.875rem;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.nav-tab:hover {
  color: var(--text-secondary);
}

.nav-tab.active {
  color: var(--accent-cyan);
  border-bottom-color: var(--accent-cyan);
}

.tab-icon {
  font-size: 1rem;
}

/* ===== Main Content ===== */
.main-content {
  flex: 1;
  max-width: 1400px;
  width: 100%;
  margin: 0 auto;
  padding: 2rem;
}

.panel {
  animation: fade-in-up 0.5s ease-out;
}

.panel-grid {
  display: grid;
  grid-template-columns: 1fr 1.5fr;
  gap: 2rem;
}

@media (max-width: 1024px) {
  .panel-grid {
    grid-template-columns: 1fr;
  }
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.panel-title {
  font-size: 1.25rem;
  color: var(--text-primary);
}

/* ===== Card ===== */
.card {
  background: var(--bg-card);
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  padding: 1.5rem;
  backdrop-filter: blur(10px);
  transition: all 0.3s;
}

.card:hover {
  border-color: var(--border-glow);
  box-shadow: var(--shadow-glow);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border-primary);
}

.card-title {
  font-size: 1rem;
  color: var(--text-primary);
}

.card-badge {
  font-size: 0.625rem;
  font-family: var(--font-mono);
  color: var(--accent-cyan);
  background: rgba(34, 211, 238, 0.1);
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  border: 1px solid rgba(34, 211, 238, 0.2);
}

/* ===== Form ===== */
.form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-row {
  display: flex;
  gap: 1rem;
}

.form-label {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex: 1;
}

.form-label.flex-1 {
  flex: 1;
}

.label-text {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.form-input,
.form-select {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-primary);
  border-radius: 6px;
  padding: 0.75rem 1rem;
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: 0.875rem;
  transition: all 0.2s;
}

.form-input:focus,
.form-select:focus {
  outline: none;
  border-color: var(--accent-cyan);
  box-shadow: 0 0 0 3px rgba(34, 211, 238, 0.1);
}

.form-select {
  cursor: pointer;
}

.form-section {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-primary);
}

.section-title {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 1rem;
}

/* ===== Buttons ===== */
.btn-primary {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 1rem 2rem;
  background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
  border: none;
  border-radius: 8px;
  color: #fff;
  font-family: var(--font-display);
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  margin-top: 1rem;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 10px 30px rgba(34, 211, 238, 0.3);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-icon {
  font-size: 0.75rem;
}

.btn-refresh {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-primary);
  border-radius: 6px;
  color: var(--text-secondary);
  font-family: var(--font-display);
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-refresh:hover {
  border-color: var(--accent-cyan);
  color: var(--accent-cyan);
}

/* ===== Loading ===== */
.loading-spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.loading-spinner.large {
  width: 24px;
  height: 24px;
  border-width: 3px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 3rem;
  color: var(--text-muted);
}

/* ===== Result Card ===== */
.result-card {
  min-height: 400px;
}

.result-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 3rem;
  color: var(--text-muted);
}

.empty-icon {
  font-size: 3rem;
  opacity: 0.3;
}

.result-error {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  color: #ef4444;
}

.result-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.result-meta {
  display: flex;
  gap: 1.5rem;
  padding: 1rem;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.meta-label {
  font-size: 0.625rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.meta-value {
  font-size: 0.875rem;
  color: var(--text-primary);
}

.experiment-group {
  padding: 0.25rem 0.5rem;
  background: rgba(139, 92, 246, 0.2);
  border-radius: 4px;
  color: var(--accent-purple);
}

.latency-badge {
  font-size: 0.75rem;
  font-family: var(--font-mono);
  color: var(--accent-green);
  background: rgba(16, 185, 129, 0.1);
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
}

/* ===== Products ===== */
.products-grid {
  display: grid;
  gap: 0.75rem;
}

.product-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--border-primary);
  border-radius: 8px;
  animation: fade-in-up 0.3s ease-out backwards;
  animation-delay: var(--delay);
  transition: all 0.2s;
}

.product-card:hover {
  border-color: var(--accent-cyan);
  transform: translateX(4px);
}

.product-rank {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 700;
  color: #fff;
}

.product-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.product-id {
  font-size: 0.625rem;
  color: var(--text-muted);
}

.product-name {
  font-size: 0.875rem;
  color: var(--text-primary);
  font-weight: 500;
}

.product-meta {
  display: flex;
  gap: 1rem;
  margin-top: 0.25rem;
}

.product-category {
  font-size: 0.75rem;
  color: var(--accent-purple);
}

.product-price {
  font-size: 0.75rem;
  color: var(--accent-green);
  font-family: var(--font-mono);
}

.product-score {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.5rem;
  background: rgba(34, 211, 238, 0.1);
  border-radius: 8px;
}

.score-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--accent-cyan);
  font-family: var(--font-mono);
}

.score-label {
  font-size: 0.5rem;
  color: var(--text-muted);
  text-transform: uppercase;
}

/* ===== Marketing Copies ===== */
.copies-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.copy-item {
  padding: 1rem;
  background: rgba(0, 0, 0, 0.2);
  border-left: 3px solid var(--accent-pink);
  border-radius: 0 8px 8px 0;
}

.copy-product {
  font-size: 0.625rem;
  color: var(--accent-pink);
  display: block;
  margin-bottom: 0.5rem;
}

.copy-text {
  font-size: 0.875rem;
  color: var(--text-secondary);
  line-height: 1.5;
}

/* ===== Agents ===== */
.agents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 0.5rem;
}

.agent-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
}

.agent-name {
  flex: 1;
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.agent-status {
  font-size: 0.875rem;
}

.agent-status.success {
  color: var(--accent-green);
}

.agent-status.failed {
  color: #ef4444;
}

.agent-latency {
  font-size: 0.625rem;
  font-family: var(--font-mono);
  color: var(--text-muted);
}

/* ===== Experiments Panel ===== */
.experiments-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 1.5rem;
}

.experiment-card {
  background: var(--bg-card);
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  padding: 1.5rem;
}

.exp-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.exp-name {
  font-size: 1rem;
  color: var(--text-primary);
}

.exp-status {
  font-size: 0.625rem;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  text-transform: uppercase;
}

.exp-status.enabled {
  background: rgba(16, 185, 129, 0.2);
  color: var(--accent-green);
}

.exp-status.disabled {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.exp-groups {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1rem;
}

.group-item {
  padding: 0.75rem;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
}

.group-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.group-name {
  font-size: 0.75rem;
  color: var(--text-primary);
}

.group-weight {
  font-size: 0.75rem;
  color: var(--accent-cyan);
  font-family: var(--font-mono);
}

.group-bar {
  height: 4px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 2px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: var(--gradient-cyber);
  border-radius: 2px;
}

.group-stats {
  display: flex;
  gap: 1rem;
  margin-top: 0.5rem;
}

.group-stats .stat {
  font-size: 0.625rem;
  color: var(--text-muted);
}

.exp-stats {
  display: flex;
  gap: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-primary);
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.stat-label {
  font-size: 0.625rem;
  color: var(--text-muted);
  text-transform: uppercase;
}

.stat-value {
  font-size: 1rem;
  color: var(--text-primary);
  font-family: var(--font-mono);
}

/* ===== Metrics Panel ===== */
.metrics-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1.5rem;
}

@media (max-width: 768px) {
  .metrics-grid {
    grid-template-columns: 1fr;
  }
}

.metrics-card {
  background: var(--bg-card);
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  padding: 1.5rem;
}

.metrics-title {
  font-size: 1rem;
  color: var(--text-primary);
  margin-bottom: 1rem;
}

.metrics-table {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.table-header,
.table-row {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  gap: 1rem;
  padding: 0.75rem;
}

.table-header {
  font-size: 0.625rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--border-primary);
}

.table-row {
  font-size: 0.875rem;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
}

.cell-name {
  color: var(--text-primary);
}

.cell-value {
  color: var(--text-secondary);
  font-family: var(--font-mono);
}

.business-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}

.biz-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
}

.biz-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--accent-cyan);
  font-family: var(--font-mono);
}

.biz-label {
  font-size: 0.75rem;
  color: var(--text-muted);
}

/* ===== Footer ===== */
.footer {
  padding: 1.5rem 2rem;
  border-top: 1px solid var(--border-primary);
  background: rgba(10, 14, 23, 0.5);
}

.footer-content {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
}

.footer-text {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.footer-divider {
  color: var(--border-primary);
}

/* ===== Vector Store Panel ===== */
.vector-panel {
  animation: fade-in-up 0.5s ease-out;
}

.vector-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
}

.connection-card .card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-badge {
  font-size: 0.625rem;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.status-badge.connected {
  background: rgba(16, 185, 129, 0.2);
  color: var(--accent-green);
}

.status-badge.disconnected {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.connection-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
}

.btn-action {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-primary);
  border-radius: 6px;
  color: var(--text-secondary);
  font-family: var(--font-display);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-action:hover:not(:disabled) {
  border-color: var(--accent-cyan);
  color: var(--accent-cyan);
}

.btn-action.primary {
  background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
  border: none;
  color: #fff;
}

.btn-action.primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(34, 211, 238, 0.3);
}

.btn-action:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.stats-content {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--border-primary);
}

.stat-row:last-child {
  border-bottom: none;
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.stat-value {
  font-size: 0.875rem;
  color: var(--text-primary);
  font-family: var(--font-mono);
}

.text-green {
  color: var(--accent-green);
}

.text-orange {
  color: var(--accent-orange);
}

.stats-empty {
  text-align: center;
  padding: 2rem;
  color: var(--text-muted);
}

.sync-card .sync-desc {
  font-size: 0.875rem;
  color: var(--text-muted);
  margin-bottom: 1rem;
  line-height: 1.5;
}

.sync-actions {
  display: flex;
  gap: 1rem;
}

.info-card .info-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.info-card .info-list li {
  font-size: 0.875rem;
  color: var(--text-secondary);
  padding-left: 1rem;
  position: relative;
  line-height: 1.5;
}

.info-card .info-list li::before {
  content: '•';
  position: absolute;
  left: 0;
  color: var(--accent-cyan);
}

.info-card .info-list strong {
  color: var(--accent-cyan);
}
</style>
