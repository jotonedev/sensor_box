__all__ = ["CAQI"]


# noinspection PyPep8Naming
class CAQI:
    CAQI: tuple[tuple[int, int], ...] = (
        (0, 25),
        (26, 50),
        (51, 75),
        (76, 100),
        (101, 1000)
    )

    _PM2_5: tuple[tuple[int, int], ...] = (
        (0, 15),
        (16, 30),
        (31, 55),
        (56, 110),
        (110, 2160)  # maybe it's wrong
    )

    _PM10_0: tuple[tuple[int, int], ...] = (
        (0, 25),
        (26, 50),
        (51, 90),
        (91, 180),
        (181, 3240)  # maybe it's wrong
    )

    @classmethod
    def PM2_5(cls, data: int) -> int:
        return cls._calculate_caqi(cls._PM2_5, data)

    @classmethod
    def PM10_0(cls, data: int) -> int:
        return cls._calculate_caqi(cls._PM10_0, data)

    @classmethod
    def _calculate_caqi(cls, breakpoints: tuple[tuple[int, int], ...], data: int) -> int:
        index: int = -1
        data_range: tuple[int, int] = (-1, 0)
        for index, data_range in enumerate(breakpoints):
            if data <= data_range[1]:
                break

        i_low, i_high = cls.CAQI[index]
        c_low, c_high = data_range
        return (i_high - i_low) // (c_high - c_low) * (data - c_low) + i_low

    @classmethod
    def caqi(cls, pm2_5_atm: int, pm10_0_atm: int) -> int:
        pm2_5 = cls.PM2_5(pm2_5_atm)
        pm10_0 = cls.PM10_0(pm10_0_atm)
        return max(pm2_5, pm10_0)
