import ReactECharts from "echarts-for-react/lib/core";
import * as echarts from "echarts/core";
import { BarChart, ScatterChart } from "echarts/charts";
import { GridComponent, TooltipComponent, MarkAreaComponent, LegendComponent } from "echarts/components";
import { SVGRenderer } from "echarts/renderers";
echarts.use([BarChart, ScatterChart, GridComponent, TooltipComponent, MarkAreaComponent, LegendComponent, SVGRenderer]);

const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
export const theme = () => ({ ink: css("--ink"), soft: css("--soft"), rule: css("--rule"), pen: css("--pen"), ok: css("--ok"), bad: css("--bad"), hold: css("--hold") });
export default function Chart({ option, height = 320, label }) {
  return <div role="img" aria-label={label}><ReactECharts echarts={echarts} option={option} style={{ height }} opts={{ renderer: "svg" }} notMerge /></div>;
}
