from core.apps.cms.services.mongo import aggregate, get_collection_name


class DashboardService:

    def __init__(self) -> None:
        self.collection = None

    def set_collection(self, collection):
        self.collection = get_collection_name(collection)

    def check_collection_name(self):
        if self.collection is None:
            raise ValueError("collection not set")

    def users_count(self) -> int:
        """Get users count

        Returns:
            int: users count
        """
        self.check_collection_name()
        return list(
            aggregate(
                self.collection,
                [{"$group": {"_id": None, "total": {"$sum": 1}}}],
            )
        )[
            0
        ]["total"]

    def get_user_chart(self) -> list:
        """new user chart

        Args:
            collection ([TODO:type]): [TODO:description]
        """
        self.check_collection_name()
        data = aggregate(
            self.collection,
            [
                {
                    "$project": {
                        "day": {
                            "$dateToString": {
                                "format": "%Y-%m-%d",
                                "date": "$created_at",
                            }
                        }
                    }
                },
                {
                    "$group": {
                        "_id": "$day",
                        "total": {"$sum": 1},
                    },
                },
                {
                    "$sort": {"_id": 1},
                },
            ],
        )

        return list(map(lambda x: {"date": x.get("_id"), "value": x.get("total")}, data))
