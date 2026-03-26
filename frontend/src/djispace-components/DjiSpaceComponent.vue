<template>
  <div ref="container" class="dji-space-component-container">
    <div v-if="loading" class="loading-placeholder">
      <p>���������...</p>
    </div>
    <div v-if="error" class="error-placeholder">
      <p>�������ʧ��: {{ error }}</p>
    </div>
  </div>
</template>

<script>
import componentConfigApi from '../api/componentConfigApi.js'

export default {
  name: 'DjiSpaceComponent',
  props: {
    componentName: {
      type: String,
      required: true
    },
    componentProps: {
      type: Object,
      default: () => ({})
    },
    config: {
      type: Object,
      default: () => ({})
    },
    // ��ѡ���ֶ�ָ������ ID��Ĭ���Զ����ɣ�
    containerId: {
      type: String,
      default: ''
    }
  },
  data() {
    return {
      loading: false,
      error: null,
      loaded: false,
      backendConfig: null
    }
  },
  mounted() {
    this.initComponent()
  },
  beforeUnmount() {
    if (this.loaded && window.FH2 && this.$refs.container) {
      this.$refs.container.innerHTML = ''
    }
  },
  methods: {
    async initComponent() {
      this.loading = true
      this.error = null

      try {
        if (!window.FH2) {
          throw new Error('FH2δ��ȷ���أ�����paas.js�Ƿ���ȷ����')
        }

        // ������ȡ��˱���Ĺ�������������ǰ�˴��븲��
        let mergedConfig = {}
        try {
          this.backendConfig = await componentConfigApi.getConfig()
          if (this.backendConfig && typeof this.backendConfig === 'object') {
            mergedConfig = { ...this.backendConfig }
          }
        } catch (err) {
          console.warn('��ȡ�������ʧ�ܣ�ʹ��ǰ�˴�������', err)
        }
        mergedConfig = { ...mergedConfig, ...(this.config || {}) }

        // demo ��Ҫ��Ĺؼ��ֶ�
        if (!mergedConfig.serverUrl || !mergedConfig.hostUrl || !mergedConfig.projectToken) {
          console.warn('FH2 ����ȱ�� serverUrl/hostUrl/projectToken�����ڡ�����������á�ҳ�油ȫ')
        }
        window.FH2.initConfig(mergedConfig)

        await this.$nextTick()

        if (!this.$refs.container) {
          throw new Error('����Ԫ�ز�����')
        }

        const containerId = this.containerId || `dji-component-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
        this.$refs.container.id = containerId

        if (!document.getElementById(containerId)) {
          throw new Error('����Ԫ��δ��ȷ����')
        }

        switch (this.componentName) {
          case 'project':
            window.FH2.loadProject(containerId)
            break
          case 'cockpit':
            window.FH2.loadCockpit(containerId, this.componentProps)
            break
          case 'wayline':
            window.FH2.loadWayline(containerId, this.componentProps)
            break
          case 'waylineCreation':
            window.FH2.loadWaylineCreation(containerId)
            break
          default:
            throw new Error(`��֧�ֵ��������: ${this.componentName}`)
        }

        this.loaded = true
      } catch (err) {
        this.error = err.message
        console.error('�������ʧ��:', err)
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.dji-space-component-container {
  width: 100%;
  height: 100%;
  position: relative;
}

.loading-placeholder,
.error-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  width: 100%;
}

.loading-placeholder p,
.error-placeholder p {
  font-size: 18px;
  color: #666;
}
</style>
