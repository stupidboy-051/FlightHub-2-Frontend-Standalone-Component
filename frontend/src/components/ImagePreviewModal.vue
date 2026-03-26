<template>
  <Teleport to="body">
    <div v-if="modelValue" class="fh-image-preview-overlay" @click.self="close">
      <div class="fh-image-preview-modal" role="dialog" aria-modal="true">
        <div class="fh-image-preview-header">
          <h3 class="fh-image-preview-title">{{ title }}</h3>
          <button class="fh-image-preview-close" type="button" @click="close">×</button>
        </div>
        <div class="fh-image-preview-body">
          <img v-if="url" class="fh-image-preview-img" :src="url" alt="预览图片" />
          <div v-else class="fh-image-preview-empty">暂无图片</div>
        </div>
        <div class="fh-image-preview-footer">
          <button class="fh-image-preview-btn" type="button" @click="close">关闭</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script>
export default {
  name: 'ImagePreviewModal',
  props: {
    modelValue: {
      type: Boolean,
      default: false
    },
    url: {
      type: String,
      default: ''
    },
    title: {
      type: String,
      default: '图片预览'
    }
  },
  emits: ['update:modelValue'],
  mounted() {
    window.addEventListener('keydown', this.onKeydown)
  },
  beforeUnmount() {
    window.removeEventListener('keydown', this.onKeydown)
  },
  methods: {
    close() {
      this.$emit('update:modelValue', false)
    },
    onKeydown(e) {
      if (!this.modelValue) return
      if (e.key === 'Escape') {
        e.preventDefault()
        this.close()
      }
    }
  }
}
</script>

<style scoped>
.fh-image-preview-overlay {
  position: fixed;
  inset: 0;
  background: rgba(10, 14, 39, 0.8);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 3200;
  padding: 20px;
}

.fh-image-preview-modal {
  width: 96vw;
  max-width: 1100px;
  background: rgba(26, 31, 58, 0.95);
  border-radius: 16px;
  border: 1px solid rgba(239, 68, 68, 0.3);
  box-shadow: 0 16px 64px rgba(0, 0, 0, 0.5), 0 0 40px rgba(239, 68, 68, 0.2);
  overflow: hidden;
}

.fh-image-preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(239, 68, 68, 0.2);
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(220, 38, 38, 0.1) 100%);
}

.fh-image-preview-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #ef4444;
}

.fh-image-preview-close {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: none;
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
  font-size: 24px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.fh-image-preview-close:hover {
  background: rgba(239, 68, 68, 0.3);
  transform: rotate(90deg);
}

.fh-image-preview-body {
  padding: 18px 20px;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 220px;
}

.fh-image-preview-img {
  max-width: 100%;
  max-height: 75vh;
  object-fit: contain;
  display: block;
  border-radius: 12px;
  border: 1px solid rgba(239, 68, 68, 0.2);
  background: rgba(10, 14, 39, 0.6);
}

.fh-image-preview-empty {
  color: #94a3b8;
  font-size: 16px;
}

.fh-image-preview-footer {
  display: flex;
  justify-content: flex-end;
  padding: 14px 20px;
  border-top: 1px solid rgba(239, 68, 68, 0.1);
}

.fh-image-preview-btn {
  padding: 10px 18px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid rgba(100, 116, 139, 0.3);
  background: rgba(100, 116, 139, 0.2);
  color: #94a3b8;
  transition: all 0.2s ease;
}

.fh-image-preview-btn:hover {
  background: rgba(100, 116, 139, 0.3);
}
</style>
