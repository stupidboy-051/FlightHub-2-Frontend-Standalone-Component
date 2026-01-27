/**
 * 全局屏幕适配工具
 * 用于将应用强制缩放至适应当前窗口大小
 */
export default class ScreenAdapter {
  constructor(options = {}) {
    this.designWidth = options.width || 1920
    this.designHeight = options.height || 1080
    this.elementSelector = options.target || '#app'
    this.element = null
    this.resizeHandler = this.resize.bind(this)
  }

  init() {
    this.element = document.querySelector(this.elementSelector)
    if (!this.element) {
      console.error(`ScreenAdapter: Element ${this.elementSelector} not found`)
      return
    }

    // 设置基础样式：固定为设计稿尺寸，并居中
    this.element.style.width = `${this.designWidth}px`
    this.element.style.height = `${this.designHeight}px`
    this.element.style.position = 'absolute'
    this.element.style.top = '50%'
    this.element.style.left = '50%'
    this.element.style.transformOrigin = 'center center'
    this.element.style.overflow = 'hidden' // 防止内部滚动溢出
    
    // 强制 body 样式以适应全屏
    document.body.style.overflow = 'hidden'
    document.body.style.margin = '0'
    document.body.style.width = '100vw'
    document.body.style.height = '100vh'
    document.body.style.backgroundColor = '#000' // 补白背景色

    this.resize()
    window.addEventListener('resize', this.resizeHandler)
  }

  resize() {
    if (!this.element) return

    const windowWidth = window.innerWidth
    const windowHeight = window.innerHeight
    
    // 计算缩放比例
    // 强制拉伸铺满 (Stretched fit) - 解决“一页显示不下”和“字体竖直”问题
    // 这种模式下，如果宽高比不一致，画面会轻微变形，但能保证完整利用屏幕
    const scaleX = windowWidth / this.designWidth
    const scaleY = windowHeight / this.designHeight
    
    // 应用缩放
    this.element.style.transform = `translate(-50%, -50%) scale(${scaleX}, ${scaleY})`
  }

  destroy() {
    window.removeEventListener('resize', this.resizeHandler)
    if (this.element) {
      this.element.style.width = ''
      this.element.style.height = ''
      this.element.style.position = ''
      this.element.style.top = ''
      this.element.style.left = ''
      this.element.style.transform = ''
      this.element.style.transformOrigin = ''
      this.element.style.overflow = ''
    }
    document.body.style.overflow = ''
    document.body.style.width = ''
    document.body.style.height = ''
    document.body.style.backgroundColor = ''
  }
}
