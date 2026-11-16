import { fireEvent, render } from '@testing-library/react';
import React, { useState } from 'react';
import { renderIntoContainer, act } from '../../_support/render';
import { NumericInputWithUnit } from '../../../src/static/js/components/_shared/numeric-input-with-unit/NumericInputWithUnit';

const persistedUnits = [
    { key: 'px', label: 'px' },
    { key: 'percent', label: '%' },
];

function ShareEmbedPair() {
    const [width, setWidth] = useState<number | string>(20);
    const [height, setHeight] = useState<number | string>(11);
    const [unitOptions] = useState(persistedUnits);

    function onWidth(newVal: string) {
        const stored = newVal === '' ? 0 : newVal;
        setWidth(stored);
        setHeight(parseInt(String((Number(stored) * 9) / 16), 10));
    }

    return (
        <div>
            <NumericInputWithUnit
                label="Width"
                valueCallback={onWidth}
                defaultValue={parseInt(String(width), 10)}
                defaultUnit="px"
                minValue={1}
                maxValue={99999}
                units={unitOptions}
            />
            <NumericInputWithUnit
                label="Height"
                defaultValue={parseInt(String(height), 10)}
                defaultUnit="px"
                minValue={1}
                maxValue={99999}
                units={unitOptions}
            />
        </div>
    );
}

function FreshUnitsParent() {
    const [value, setValue] = useState(20);
    const [tick, setTick] = useState(0);

    return (
        <div>
            <NumericInputWithUnit
                defaultValue={value}
                defaultUnit="px"
                units={[
                    { key: 'px', label: 'px' },
                    { key: 'percent', label: '%' },
                ]}
                valueCallback={(next: string) => setValue(next === '' ? 0 : Number(next))}
            />
            <button type="button" onClick={() => setTick((n) => n + 1)}>
                re-render
            </button>
            <span hidden>{tick}</span>
        </div>
    );
}

function setNativeValue(el: HTMLInputElement | HTMLSelectElement, value: string) {
    const proto = el instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
    (Object.getOwnPropertyDescriptor(proto, 'value') as PropertyDescriptor).set!.call(el, value);
}

describe('components/_shared', () => {
    describe('NumericInputWithUnit', () => {
        const units = [{ key: 'px', label: 'Pixels' }, { key: 'percent' }, { label: 'ignored without key' }];

        test('Renders label, bounded input and unit options', () => {
            const { container, unmount } = renderIntoContainer(
                <NumericInputWithUnit
                    label="Width"
                    units={units}
                    defaultValue={50}
                    minValue={10}
                    maxValue={100}
                    defaultUnit="percent"
                />
            );
            expect(container.querySelector('.num-value-unit .label')?.textContent).toBe('Width');
            const input = container.querySelector('input.value-input') as HTMLInputElement;
            expect(input.value).toBe('50');
            expect(input.getAttribute('min')).toBe('10');
            expect(input.getAttribute('max')).toBe('100');

            const select = container.querySelector('select.value-unit') as HTMLSelectElement;
            const options = Array.from(select.options).map((o) => [o.value, o.textContent]);
            expect(options).toStrictEqual([
                ['px', 'Pixels'],
                ['percent', 'percent'],
            ]);
            expect(select.value).toBe('percent');
            unmount();
        });

        test.each([
            [5, 10],
            [500, 100],
        ])('Clamps default value %p into range as %p', (defaultValue, expected) => {
            const { container, unmount } = renderIntoContainer(
                <NumericInputWithUnit units={units} defaultValue={defaultValue} minValue={10} maxValue={100} />
            );
            expect((container.querySelector('input') as HTMLInputElement).value).toBe(String(expected));
            unmount();
        });

        test('Falls back to the first unit for unknown default unit and omits label and bounds', () => {
            const { container, unmount } = renderIntoContainer(
                <NumericInputWithUnit units={units} defaultValue={1} defaultUnit="em" />
            );
            expect(container.querySelector('.label')).toBeNull();
            const input = container.querySelector('input') as HTMLInputElement;
            expect(input.hasAttribute('min')).toBe(false);
            expect(input.hasAttribute('max')).toBe(false);
            expect((container.querySelector('select') as HTMLSelectElement).value).toBe('px');
            unmount();
        });

        test('Renders an empty select without units', () => {
            const { container, unmount } = renderIntoContainer(<NumericInputWithUnit units={[]} defaultValue={1} />);
            expect((container.querySelector('select') as HTMLSelectElement).options).toHaveLength(0);
            unmount();
        });

        test('Forwards user changes to value and unit callbacks', () => {
            const valueCallback = jest.fn();
            const unitCallback = jest.fn();
            const { container, unmount } = renderIntoContainer(
                <NumericInputWithUnit
                    units={units}
                    defaultValue={20}
                    valueCallback={valueCallback}
                    unitCallback={unitCallback}
                />
            );
            const input = container.querySelector('input') as HTMLInputElement;
            const select = container.querySelector('select') as HTMLSelectElement;

            act(() => {
                setNativeValue(input, '42');
                input.dispatchEvent(new Event('input', { bubbles: true }));
            });
            expect(valueCallback).toHaveBeenCalledWith('42');

            act(() => {
                setNativeValue(select, 'percent');
                select.dispatchEvent(new Event('change', { bubbles: true }));
            });
            expect(unitCallback).toHaveBeenCalledWith('percent');
            unmount();
        });

        test('Accepts changes without callbacks', () => {
            const { container, unmount } = renderIntoContainer(
                <NumericInputWithUnit units={units} defaultValue={20} />
            );
            const input = container.querySelector('input') as HTMLInputElement;
            const select = container.querySelector('select') as HTMLSelectElement;
            expect(() =>
                act(() => {
                    setNativeValue(input, '7');
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    setNativeValue(select, 'percent');
                    select.dispatchEvent(new Event('change', { bubbles: true }));
                })
            ).not.toThrow();
            unmount();
        });
    });

    describe('rendered value persists (#124)', () => {
        test('typed value and unit persist across a re-render', () => {
            const props = {
                defaultValue: 20,
                defaultUnit: 'px',
                units: persistedUnits,
            };
            const { container, rerender } = render(<NumericInputWithUnit {...props} />);
            const input = container.querySelector('input.value-input') as HTMLInputElement;
            const select = container.querySelector('select.value-unit') as HTMLSelectElement;

            fireEvent.change(input, { target: { value: '' } });
            fireEvent.change(input, { target: { value: '4' } });
            fireEvent.change(input, { target: { value: '42' } });
            fireEvent.change(select, { target: { value: 'percent' } });

            rerender(<NumericInputWithUnit {...props} />);

            expect(input.value).toBe('42');
            expect(select.value).toBe('percent');
        });

        test('share-embed-like pair keeps a cleared width and applies the aspect ratio', () => {
            const { container } = render(<ShareEmbedPair />);
            const width = () => container.querySelectorAll('input.value-input')[0] as HTMLInputElement;
            const height = () => container.querySelectorAll('input.value-input')[1] as HTMLInputElement;

            fireEvent.change(width(), { target: { value: '' } });
            expect(width().value).toBe('');

            fireEvent.change(width(), { target: { value: '640' } });
            expect(width().value).toBe('640');
            expect(height().value).toBe('360');
        });

        test('a bounds-only prop change reclamps the displayed value', () => {
            const { container, rerender } = render(
                <NumericInputWithUnit
                    defaultValue={20}
                    defaultUnit="px"
                    minValue={1}
                    maxValue={100}
                    units={persistedUnits}
                />
            );
            const input = () => container.querySelector('input.value-input') as HTMLInputElement;
            expect(input().value).toBe('20');

            rerender(
                <NumericInputWithUnit
                    defaultValue={20}
                    defaultUnit="px"
                    minValue={1}
                    maxValue={10}
                    units={persistedUnits}
                />
            );
            expect(input().value).toBe('10');

            rerender(
                <NumericInputWithUnit
                    defaultValue={20}
                    defaultUnit="px"
                    minValue={30}
                    maxValue={100}
                    units={persistedUnits}
                />
            );
            expect(input().value).toBe('30');
        });

        test('a real parent prop change still applies, clamped', () => {
            const { container, rerender } = render(
                <NumericInputWithUnit defaultValue={20} defaultUnit="px" units={persistedUnits} />
            );

            rerender(
                <NumericInputWithUnit defaultValue={150} defaultUnit="percent" maxValue={100} units={persistedUnits} />
            );

            expect((container.querySelector('input.value-input') as HTMLInputElement).value).toBe('100');
            expect((container.querySelector('select.value-unit') as HTMLSelectElement).value).toBe('percent');
        });

        test('fresh units array on every render does not reset a typed value', () => {
            const { container, getByRole } = render(<FreshUnitsParent />);
            const input = () => container.querySelector('input.value-input') as HTMLInputElement;

            fireEvent.change(input(), { target: { value: '' } });
            expect(input().value).toBe('');

            fireEvent.change(input(), { target: { value: '4' } });
            fireEvent.change(input(), { target: { value: '42' } });
            fireEvent.click(getByRole('button', { name: 're-render' }));

            expect(input().value).toBe('42');
        });
    });
});
