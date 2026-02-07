import React from "react";
import { parseISO, format, addDays } from "date-fns";
import { strftimeToDateFns } from "@/utils/date-format";

const LayerTimeSentence = ({ config, params }) => {
  if (config.param && params && params[config.param]) {
    let time = params[config.param];

    try {
      time = parseISO(time);
      // Convert Python strftime format to date-fns format if needed
      let dateFormat = config.format || "do MMM y";
      if (dateFormat.includes("%")) {
        dateFormat = strftimeToDateFns(dateFormat);
      }
      let formatted = time && format(time, dateFormat);

      if (config.add && !isNaN(config.add)) {
        const end = addDays(time, config.add);
        formatted = `${formatted} to ${format(end, dateFormat)}`;
      }

      if (config.template) {
        formatted = config.template.replace("{time}", formatted);
      }

      return <div>{formatted}</div>;
    } catch (error) {
      return null;
    }
  }

  return null;
};

export default LayerTimeSentence;
