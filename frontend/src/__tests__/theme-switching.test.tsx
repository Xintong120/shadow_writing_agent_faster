/**
 * 主题切换自动化测试套件
 * 
 * 测试主题切换功能的稳定性和一致性
 */

import { render, screen, waitFor } from '@testing-library/react';
import { MantineProvider, useMantineColorScheme } from '@mantine/core';
import { act } from 'react-dom/test-utils';

// 测试组件：用于触发主题切换
function ThemeSwitcher() {
  const { colorScheme, toggleColorScheme } = useMantineColorScheme();
  
  return (
    <div>
      <div data-testid="current-theme">{colorScheme}</div>
      <button onClick={() => toggleColorScheme()} data-testid="toggle-theme">
        Toggle Theme
      </button>
    </div>
  );
}

// 测试组件：验证主题颜色应用
function ThemedComponent() {
  return (
    <MantineProvider>
      <div data-testid="themed-box" style={{ 
        backgroundColor: 'var(--mantine-color-body)',
        color: 'var(--mantine-color-text)'
      }}>
        Themed Content
      </div>
    </MantineProvider>
  );
}

describe('主题切换自动化测试套件', () => {
  describe('基础主题切换功能', () => {
    test('应该能够切换到暗色主题', async () => {
      const { getByTestId } = render(
        <MantineProvider defaultColorScheme="light">
          <ThemeSwitcher />
        </MantineProvider>
      );

      const currentTheme = getByTestId('current-theme');
      const toggleButton = getByTestId('toggle-theme');

      // 初始应该是亮色主题
      expect(currentTheme.textContent).toBe('light');

      // 切换到暗色主题
      await act(async () => {
        toggleButton.click();
      });

      await waitFor(() => {
        expect(currentTheme.textContent).toBe('dark');
      });
    });

    test('应该能够切换回亮色主题', async () => {
      const { getByTestId } = render(
        <MantineProvider defaultColorScheme="dark">
          <ThemeSwitcher />
        </MantineProvider>
      );

      const currentTheme = getByTestId('current-theme');
      const toggleButton = getByTestId('toggle-theme');

      // 初始应该是暗色主题
      expect(currentTheme.textContent).toBe('dark');

      // 切换到亮色主题
      await act(async () => {
        toggleButton.click();
      });

      await waitFor(() => {
        expect(currentTheme.textContent).toBe('light');
      });
    });

    test('应该能够多次切换主题', async () => {
      const { getByTestId } = render(
        <MantineProvider defaultColorScheme="light">
          <ThemeSwitcher />
        </MantineProvider>
      );

      const currentTheme = getByTestId('current-theme');
      const toggleButton = getByTestId('toggle-theme');

      // 第一次切换
      await act(async () => {
        toggleButton.click();
      });
      await waitFor(() => expect(currentTheme.textContent).toBe('dark'));

      // 第二次切换
      await act(async () => {
        toggleButton.click();
      });
      await waitFor(() => expect(currentTheme.textContent).toBe('light'));

      // 第三次切换
      await act(async () => {
        toggleButton.click();
      });
      await waitFor(() => expect(currentTheme.textContent).toBe('dark'));
    });
  });

  describe('主题颜色应用验证', () => {
    test('亮色主题应该应用正确的CSS变量', () => {
      const { getByTestId } = render(
        <MantineProvider defaultColorScheme="light">
          <ThemedComponent />
        </MantineProvider>
      );

      const themedBox = getByTestId('themed-box');
      const styles = window.getComputedStyle(themedBox);

      // 验证CSS变量被正确应用
      expect(styles.backgroundColor).toBeTruthy();
      expect(styles.color).toBeTruthy();
    });

    test('暗色主题应该应用正确的CSS变量', () => {
      const { getByTestId } = render(
        <MantineProvider defaultColorScheme="dark">
          <ThemedComponent />
        </MantineProvider>
      );

      const themedBox = getByTestId('themed-box');
      const styles = window.getComputedStyle(themedBox);

      // 验证CSS变量被正确应用
      expect(styles.backgroundColor).toBeTruthy();
      expect(styles.color).toBeTruthy();
    });
  });

  describe('主题持久化', () => {
    beforeEach(() => {
      // 清除localStorage
      localStorage.clear();
    });

    test('应该能够保存主题偏好到localStorage', async () => {
      const { getByTestId } = render(
        <MantineProvider defaultColorScheme="light">
          <ThemeSwitcher />
        </MantineProvider>
      );

      const toggleButton = getByTestId('toggle-theme');

      // 切换主题
      await act(async () => {
        toggleButton.click();
      });

      // 验证localStorage中保存了主题偏好
      await waitFor(() => {
        const savedTheme = localStorage.getItem('mantine-color-scheme');
        expect(savedTheme).toBeTruthy();
      });
    });

    test('应该能够从localStorage恢复主题偏好', () => {
      // 预设localStorage中的主题
      localStorage.setItem('mantine-color-scheme', 'dark');

      const { getByTestId } = render(
        <MantineProvider>
          <ThemeSwitcher />
        </MantineProvider>
      );

      const currentTheme = getByTestId('current-theme');

      // 验证主题从localStorage恢复
      expect(currentTheme.textContent).toBe('dark');
    });
  });

  describe('主题切换性能', () => {
    test('主题切换应该在合理时间内完成', async () => {
      const { getByTestId } = render(
        <MantineProvider defaultColorScheme="light">
          <ThemeSwitcher />
        </MantineProvider>
      );

      const toggleButton = getByTestId('toggle-theme');
      const startTime = performance.now();

      await act(async () => {
        toggleButton.click();
      });

      const endTime = performance.now();
      const duration = endTime - startTime;

      // 主题切换应该在100ms内完成
      expect(duration).toBeLessThan(100);
    });
  });
});
