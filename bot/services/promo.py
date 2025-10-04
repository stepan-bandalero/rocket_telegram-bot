import secrets
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, exists
from bot.models.promo import PromoLink, PromoReferral
from bot.models.users import User
from bot.models.user_gift import UserGift

from bot.models.user_transaction import UserTransaction
from bot.models.withdraw_request import WithdrawRequest
from bot.models.gift_withdrawals import GiftWithdrawal


class PromoService:
    @staticmethod
    async def create_promo(session: AsyncSession, created_by: int, referral_percentage: int):
        import secrets
        code = secrets.token_urlsafe(6)
        promo = PromoLink(
            code=code,
            created_by=created_by,
            referral_percentage=referral_percentage
        )
        session.add(promo)
        await session.commit()
        await session.refresh(promo)
        return promo

    # async def create_promo(session: AsyncSession, created_by: int) -> PromoLink:
    #     while True:
    #         code = secrets.token_hex(4)
    #         exists_query = await session.execute(
    #             select(PromoLink).where(PromoLink.code == code)
    #         )
    #         if not exists_query.scalar_one_or_none():
    #             break
    #
    #     promo = PromoLink(code=code, created_by=created_by)
    #     session.add(promo)
    #     await session.commit()
    #     await session.refresh(promo)
    #     return promo



    # @staticmethod
    # async def get_promos(session: AsyncSession):
    #     # считаем количество переходов и активных пользователей
    #     result = await session.execute(
    #         select(
    #             PromoLink.id,
    #             PromoLink.code,
    #             PromoLink.created_by,  # ✅ добавляем владельца ссылки
    #             func.count(PromoReferral.id).label("referrals_count"),
    #             func.count(func.nullif(User.telegram_id, None)).label("users_count"),
    #         )
    #         .outerjoin(PromoReferral, PromoReferral.promo_id == PromoLink.id)
    #         .outerjoin(User, User.telegram_id == PromoReferral.user_id)
    #         .group_by(PromoLink.id)
    #     )
    #     promos = result.all()
    #
    #     data = []
    #     for promo_id, code, created_by, referrals_count, users_count in promos:
    #         from sqlalchemy import or_
    #
    #         active_query = await session.execute(
    #             select(func.count())
    #             .select_from(User)
    #             .outerjoin(UserGift, UserGift.user_id == User.telegram_id)
    #             .where(
    #                 User.telegram_id.in_(
    #                     select(PromoReferral.user_id).where(PromoReferral.promo_id == promo_id)
    #                 ),
    #                 or_(
    #                     UserGift.id.isnot(None),
    #                     User.telegram_id.in_(
    #                         select(User.telegram_id).where(User.ton_balance > 0)
    #                     )
    #                 )
    #             )
    #         )
    #
    #         active_users = active_query.scalar() or 0
    #
    #         data.append({
    #             "id": promo_id,
    #             "code": code,
    #             "created_by": created_by,  # ✅ возвращаем в словарь
    #             "referrals_count": referrals_count,
    #             "active_users": active_users
    #         })
    #     return data

    # @staticmethod
    # async def get_promos(session: AsyncSession):
    #
    #     # ----------------------------------------------------
    #
    #     # 1) Базовая выборка: промо + количество переходов + пользователей
    #     result = await session.execute(
    #         select(
    #             PromoLink.id,
    #             PromoLink.code,
    #             PromoLink.created_by,
    #             func.count(PromoReferral.id).label("referrals_count"),
    #             func.count(func.nullif(User.telegram_id, None)).label("users_count"),
    #         )
    #         .outerjoin(PromoReferral, PromoReferral.promo_id == PromoLink.id)
    #         .outerjoin(User, User.telegram_id == PromoReferral.user_id)
    #         .group_by(PromoLink.id, PromoLink.code, PromoLink.created_by)
    #     )
    #     promos = result.all()
    #
    #     data = []
    #     for promo_id, code, created_by, referrals_count, users_count in promos:
    #         # если у промо нет рефералов — сразу нули
    #         if not referrals_count:
    #             active_users = 0
    #             total_deposits = 0
    #             total_withdrawals = 0
    #         else:
    #             # подзапрос списка user_id для данного promo_id
    #             referrals_subq = select(PromoReferral.user_id).where(PromoReferral.promo_id == promo_id)
    #
    #             # 2) Активные пользователи — distinct user_id из user_transactions с type='deposit'
    #             active_q = await session.execute(
    #                 select(func.count(func.distinct(UserTransaction.user_id)))
    #                 .where(
    #                     UserTransaction.user_id.in_(referrals_subq),
    #                     UserTransaction.type == "deposit",
    #                 )
    #             )
    #             active_users = int(active_q.scalar() or 0)
    #
    #             # 3) Сумма всех пополнений рефералов (user_transactions.type='deposit')
    #             deposits_q = await session.execute(
    #                 select(func.coalesce(func.sum(UserTransaction.amount), 0))
    #                 .where(
    #                     UserTransaction.user_id.in_(referrals_subq),
    #                     UserTransaction.type == "deposit",
    #                 )
    #             )
    #             total_deposits = int(deposits_q.scalar() or 0)
    #
    #             # 4) Сумма выводов TON: withdraw_requests.status='done'
    #             ton_with_q = await session.execute(
    #                 select(func.coalesce(func.sum(WithdrawRequest.amount), 0))
    #                 .where(
    #                     WithdrawRequest.user_id.in_(referrals_subq),
    #                     WithdrawRequest.status == "done",
    #                 )
    #             )
    #             ton_withdrawals = int(ton_with_q.scalar() or 0)
    #
    #             # 5) Сумма выводов подарков: gift_withdrawals.status='done'
    #             gift_with_q = await session.execute(
    #                 select(func.coalesce(func.sum(GiftWithdrawal.purchase_price_cents), 0))
    #                 .where(
    #                     GiftWithdrawal.user_id.in_(referrals_subq),
    #                     GiftWithdrawal.status == "done",
    #                 )
    #             )
    #             gift_withdrawals = int(gift_with_q.scalar() or 0)
    #
    #             total_withdrawals = ton_withdrawals + gift_withdrawals
    #
    #         data.append({
    #             "id": promo_id,
    #             "code": code,
    #             "created_by": created_by,
    #             "referrals_count": int(referrals_count or 0),
    #             "users_count": int(users_count or 0),
    #             "active_users": int(active_users),
    #             # суммы возвращаем в тех единицах, в которых хранятся в БД (cents/DB-units)
    #             "total_deposits_cents": int(total_deposits),
    #             "total_withdrawals_cents": int(total_withdrawals),
    #         })
    #
    #     return data

    @staticmethod
    async def get_promos(session: AsyncSession):
        # 1) Базовая выборка: промо + количество переходов + пользователей + процент
        result = await session.execute(
            select(
                PromoLink.id,
                PromoLink.code,
                PromoLink.created_by,
                PromoLink.referral_percentage,
                func.count(PromoReferral.id).label("referrals_count"),
                func.count(func.nullif(User.telegram_id, None)).label("users_count"),
            )
            .outerjoin(PromoReferral, PromoReferral.promo_id == PromoLink.id)
            .outerjoin(User, User.telegram_id == PromoReferral.user_id)
            .group_by(
                PromoLink.id,
                PromoLink.code,
                PromoLink.created_by,
                PromoLink.referral_percentage,
            )
        )

        promos = result.all()
        data = []

        for promo_id, code, created_by, referral_percentage, referrals_count, users_count in promos:
            if not referrals_count:
                active_users = 0
                total_deposits = 0
                total_withdrawals = 0
            else:
                referrals_subq = select(PromoReferral.user_id).where(PromoReferral.promo_id == promo_id)

                # активные
                active_q = await session.execute(
                    select(func.count(func.distinct(UserTransaction.user_id)))
                    .where(
                        UserTransaction.user_id.in_(referrals_subq),
                        UserTransaction.type == "deposit",
                    )
                )
                active_users = int(active_q.scalar() or 0)

                # пополнения
                deposits_q = await session.execute(
                    select(func.coalesce(func.sum(UserTransaction.amount), 0))
                    .where(
                        UserTransaction.user_id.in_(referrals_subq),
                        UserTransaction.type == "deposit",
                    )
                )
                total_deposits = int(deposits_q.scalar() or 0)

                # выводы TON
                ton_with_q = await session.execute(
                    select(func.coalesce(func.sum(WithdrawRequest.amount), 0))
                    .where(
                        WithdrawRequest.user_id.in_(referrals_subq),
                        WithdrawRequest.status == "done",
                    )
                )
                ton_withdrawals = int(ton_with_q.scalar() or 0)

                # выводы подарков
                gift_with_q = await session.execute(
                    select(func.coalesce(func.sum(GiftWithdrawal.purchase_price_cents), 0))
                    .where(
                        GiftWithdrawal.user_id.in_(referrals_subq),
                        GiftWithdrawal.status == "done",
                    )
                )
                gift_withdrawals = int(gift_with_q.scalar() or 0)

                total_withdrawals = ton_withdrawals + gift_withdrawals

            data.append({
                "id": promo_id,
                "code": code,
                "created_by": created_by,
                "referral_percentage": int(referral_percentage or 0),
                "referrals_count": int(referrals_count or 0),
                "users_count": int(users_count or 0),
                "active_users": int(active_users),
                "total_deposits_cents": int(total_deposits),
                "total_withdrawals_cents": int(total_withdrawals),
            })

        return data

    @staticmethod
    async def delete_promo(session: AsyncSession, promo_code: str):
        result = await session.execute(
            select(PromoLink).where(PromoLink.code == promo_code)
        )
        promo = result.scalars().first()
        if promo:
            await session.delete(promo)
            await session.commit()
            return True
        return False

