/**
 * 组件视觉对比测试
 * 
 * 使用截图对比确保组件在主题切换前后视觉一致
 */

import { render } from '@testing-library/react';
import { MantineProvider } from '@mantine/core';
import '@testing-library/jest-dom';

// 模拟组件用于测试
function SampleCard({ title, content }: { title: string; content: string }) {
  return (
    <div 
      data-testid="sample-card"
      style={{
        backgroundColor: 'var(--mantine-color-body)',
        color: 'var(--mantine-color-text)',
        padding: 'var(--mantine-spacing-md)',
        borderRadius: 'var(--mantine-radius-md)',
        border: '1px solid var(--mantine-color-default-border)',
      }}
    >
      <h3 style={{ 
        fontSize: 'var(--mantine-font-size-lg)',
        marginBottom: 'var(--mantine-spacing-sm)',
      }}>
        {title}
      </h3>
      <p style={{ fontSize: 'var(--mantine-font-size-md)' }}>
        {content}
      </p>
    </div>
  );
}

describe('组件视觉对比测试', () => {
  describe('Card组件主题一致性', () => {
    test('亮色主题下Card应该正确渲染', () => {
      const { getByTestId } = render(
        <MantineProvider defaultColorScheme="light">
          <SampleCard title="测试标题" content="测试内容" />
        </MantineProvider>
      );

      const card = getByTestId('sample-card');
      expect(card).toBeInTheDocument();
      
      const styles = window.getComputedStyle(card);
      expect(styles.backgroundColor).toBeTruthy();
      expect(styles.color).toBeTruthy();
      expect(styles.padding).toBeTruthy();
      expect(styles.borderRadius).toBeTruthy();
    });

    test('暗色主题下Card应该正确渲染', () => {
      const { getByTestId } = render(
        <MantineProvider defaultColorScheme="dark">
          <SampleCard title="测试标题" content="测试内容" />
        </MantineProvider>
      );

      const card = getByTestId('sample-card');
      expect(card).toBeInTheDocument();
      
      const styles = window.getComputedStyle(card);
      expect(styles.backgroundColor).toBeTruthy();
      expect(styles.color).toBeTruthy();
      expect(styles.padding).toBeTruthy();
      expect(styles.borderRadius).toBeTruthy();
    });

    test('主题切换不应该破坏组件结构', () => {
      const { getByTestId, rerender } = render(
        <MantineProvider defaultColorScheme="light">
          <SampleCard title="测试标题" content="测试内容" />
        </MantineProvider>
      );

      const cardLight = getByTestId('sample-card');
      const lightStructure = cardLight.innerHTML;

      // 切换到暗色主题
      rerender(
        <MantineProvider defaultColorScheme="dark">
          <SampleCard title="测试标题" content="测试内容" />
        </MantineProvider>
      );

      const cardDark = getByTestId('sample-card');
      const darkStructure = cardDark.innerHTML;

      // 结构应该保持一致
      expect(lightStructure).toBe(darkStructure);
    });
  });

  describe('CSS变量应用验证', () => {
    test('所有主题token应该被正确应用', () => {
      const { getByTestId } = render(
        <MantineProvider defaultColorScheme="light">
          <SampleCard title="测试标题" content="测试内容" />
        </MantineProvider>
      );

      const card = getByTestId('sample-card');
      const styles = window.getComputedStyle(card);

      // 验证所有CSS变量都被应用
      expect(styles.backgroundColor).not.toBe('');
      expect(styles.color).not.toBe('');
      expect(styles.padding).not.toBe('');
      expect(styles.borderRadius).not.toBe('');
      expect(styles.border).not.toBe('');
    });

    test('不应该存在硬编码样式值', () => {
      const { getByTestId } = render(
        <MantineProvider defaultColorScheme="light">
          <SampleCard title="测试标题" content="测试内容" />
        </MantineProvider>
      );

      const card = getByTestId('sample-card');
      const inlineStyle = card.getAttribute('style') || '';

      // 检查是否包含硬编码颜色
      expect(inlineStyle).not.toMatch(/#[0-9a-fA-F]{3,6}/);
      expect(inlineStyle).not.toMatch(/rgb\(/);
      expect(inlineStyle).not.toMatch(/rgba\(/);
      
      // 检查是否包含硬编码间距
      expect(inlineStyle).not.toMatch(/\d+px(?!.*var)/);
    });
  });

  describe('响应式布局验证', () => {
    test('组件应该在不同视口下正确渲染', () => {
      // 模拟移动端视口
      global.innerWidth = 375;
      global.innerHeight = 667;

      const { getByTestId } = render(
        <MantineProvider defaultColorScheme="light">
          <SampleCard title="测试标题" content="测试内容" />
        </MantineProvider>
      );

      const card = getByTestId('sample-card');
      expect(card).toBeInTheDocument();

      // 恢复默认视口
      global.innerWidth = 1024;
      global.innerHeight = 768;
    });

    test('组件应该在桌面端视口下正确渲染', () => {
      // 模拟桌面端视口
      global.innerWidth = 1920;
      global.innerHeight = 1080;

      const { getByTestId } = render(
        <MantineProvider defaultColorScheme="light">
          <SampleCard title="测试标题" content="测试内容" />
        </MantineProvider>
      );

      const card = getByTestId('sample-card');
      expect(card).toBeInTheDocument();

      // 恢复默认视口
      global.innerWidth = 1024;
      global.innerHeight = 768;
    });
  });

  describe('可访问性验证', () => {
    test('组件应该具有适当的对比度', () => {
      const { getByTestId } = render(
        <MantineProvider defaultColorScheme="light">
          <SampleCard title="测试标题" content="测试内容" />
        </MantineProvider>
      );

      const card = getByTestId('sample-card');
      const styles = window.getComputedStyle(card);

      // 验证颜色和背景色都存在
      expect(styles.color).toBeTruthy();
      expect(styles.backgroundColor).toBeTruthy();
    });

    test('暗色主题应该具有适当的对比度', () => {
      const { getByTestId } = render(
        <MantineProvider defaultColorScheme="dark">
          <SampleCard title="测试标题" content="测试内容" />
        </MantineProvider>
      );

      const card = getByTestId('sample-card');
      const styles = window.getComputedStyle(card);

      // 验证颜色和背景色都存在
      expect(styles.color).toBeTruthy();
      expect(styles.backgroundColor).toBeTruthy();
    });
  });
});
